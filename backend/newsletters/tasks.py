import logging
from celery import shared_task, chord
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from newsletters.models import Newsletter, NewsletterTask
from users.models import User

logger = logging.getLogger(__name__)


def _get_friendly_error(error_exception):
    err_str = str(error_exception).lower()

    mapping = {
        "chat not found": "Чат не найден (пользователь не начинал диалог с ботом)",
        "bot was blocked by the user": "Пользователь заблокировал бота",
        "user is deactivated": "Аккаунт пользователя удален",
        "message is too long": "Текст сообщения слишком длинный",
        "have no rights to send a message": "У бота нет прав для отправки в этот чат",
    }

    for key, translation in mapping.items():
        if key in err_str:
            return translation

    return f"Ошибка Telegram: {str(error_exception)}"


def _finalize_individual_task(task, channels_sent, errors):
    if channels_sent:
        task.status = 'sent'
        task.channel_sent = 'both' if len(channels_sent) > 1 else channels_sent[0]
        task.sent_at = timezone.now()
    else:
        task.status = 'failed'
        task.error_message = "; ".join(errors) if errors else "Unknown error"
    task.save()




@shared_task(bind=True, max_retries=3, name='tasks.send_newsletter_task')
def send_newsletter_task(self, newsletter_id):
    try:
        newsletter = Newsletter.objects.get(pk=newsletter_id)

        if newsletter.status not in ['sending', 'scheduled']:
            return 'Newsletter is cancelled'

        recipients = User.objects.filter(is_superuser=False)

        if newsletter.only_paid:
            recipients = recipients.filter(paid=True)

        user_ids = list(recipients.values_list('id', flat=True))

        if not user_ids:
            newsletter.status = 'failed'
            newsletter.save(update_fields=['status'])
            return "No recipients"

        newsletter.total = len(user_ids)
        newsletter.save(update_fields=['total', 'status'])

        header = [send_message_to_user.s(newsletter_id, uid) for uid in user_ids]
        callback = finalize_newsletter_status.s(newsletter_id)

        chord(header)(callback)

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2)
def send_message_to_user(self, newsletter_id, user_id):
    from bot.bot import bot  

    try:
        newsletter = Newsletter.objects.prefetch_related('images').get(pk=newsletter_id)
        user = User.objects.get(pk=user_id, is_superuser=False)

        task, created = NewsletterTask.objects.get_or_create(
            newsletter=newsletter,
            user=user,
            defaults={'status': 'pending'}
        )

        if user.is_superuser:
            return "Skipped superuser"

        if task.status == 'sent':
            return "Already sent"

        channels_sent = []
        errors = []

        can_email = newsletter.channel in ['email', 'both'] and user.email
        can_tg = newsletter.channel in ['telegram', 'both'] and user.telegram_chat_id

        if not (can_email or can_tg):
            task.status = 'failed'
            task.error_message = "Нет доступных контактов (email/telegram)"
            task.save()
            return "Missing contact info"

        
        if can_email:
            try:
                html_message = render_to_string('newsletters/email.html', {
                    'newsletter': newsletter,
                    'user': user,
                    'base_url': settings.BASE_URL
                })
                send_mail(
                    subject=newsletter.title,
                    message=newsletter.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                    html_message=html_message,
                )
                channels_sent.append('email')
            except Exception as e:
                errors.append(f"Email error: {str(e)}")

        
        if can_tg:
            try:
                
                images = newsletter.images.all()
                if images.exists():
                    bot.send_cached_media_group(chat_id=user.telegram_chat_id, queryset_of_images=images)
                
                
                bot.send_message(user.telegram_chat_id, text=newsletter.message, parse_mode='HTML')
                channels_sent.append('telegram')
            except Exception as e:
                
                errors.append(_get_friendly_error(e))

        _finalize_individual_task(task, channels_sent, errors)
        return f"Processed user {user_id}"

    except Exception as exc:
        
        if self.request.retries >= self.max_retries:
            logger.error(f"Max retries hit for user {user_id} in newsletter {newsletter_id}. Failsafe activated.")
            NewsletterTask.objects.filter(newsletter_id=newsletter_id, user_id=user_id).update(
                status='failed', 
                error_message='Внутренняя системная ошибка (БД/Celery)'
            )
            return "Failed after max retries"
            
        logger.error(f"Error for user {user_id} in newsletter {newsletter_id}: {exc}")
        raise self.retry(exc=exc, countdown=180)


@shared_task
def finalize_newsletter_status(results, newsletter_id):
    try:
        newsletter = Newsletter.objects.get(pk=newsletter_id)
        stats = newsletter.tasks.all().values_list('status', flat=True)

        total = len(stats)
        sent_count = sum(1 for s in stats if s == 'sent')
        failed_count = sum(1 for s in stats if s == 'failed')

        if failed_count == 0 and sent_count > 0:
            newsletter.status = 'sent'
        elif sent_count == 0:
            newsletter.status = 'failed'
        else:
            newsletter.status = 'partial'

        newsletter.sent_at = timezone.now()
        newsletter.save(update_fields=['status', 'sent_at'])

        return f"Newsletter {newsletter_id} finished with status {newsletter.status}"
    except Newsletter.DoesNotExist:
        return "Newsletter not found"