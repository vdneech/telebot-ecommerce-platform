import logging
from django.utils import timezone
from django.db import transaction

from bot.handlers.invoices import send_invoice
from bot.bot import bot
from users.models import User
from telebot import types
from bot.models import RegistrationStep, Configuration

logger = logging.getLogger(__name__)


def extract_value(message: types.Message, step: RegistrationStep) -> str:
    """Извлекает текстовые или контактные данные из сообщения на основе требуемого типа поля."""
    if step.field_type == 'phone':
        if getattr(message, 'contact', None) and message.contact.phone_number:
            return message.contact.phone_number
            
    return (message.text or '').strip()


def is_in_registration(message: types.Message) -> bool:
    """Проверяет, находится ли пользователь в данный момент в процессе регистрации."""
    if message.content_type == 'text' and message.text and message.text.startswith('/'):
        return False

    return User.objects.filter(
        telegram_chat_id=message.from_user.id,
        is_registered=False,
        registration_step__isnull=False
    ).exists()


def is_registration_open(config: Configuration) -> tuple[bool, str]:
    """
    Проверяет, разрешена ли регистрация новых пользователей, исходя из даты и максимального лимита пользователей.
    Возвращает (is_open, error_message).
    """
    if config.end_of_registration and config.end_of_registration < timezone.now().date():
        logger.info("Registration closed: deadline passed.")
        return False, config.closed_registrations_message

    if User.objects.count() >= config.max_users:
        logger.info("Registration closed: maximum user limit reached.")
        return False, config.closed_registrations_message

    return True, ""


@bot.message_handler(func=is_in_registration, content_types=['text', 'contact'])
def registration_message_handler(message: types.Message):
    """Обрабатывает входящие данные для текущего этапа регистрации."""
    user = User.objects.select_related('registration_step').get(
        telegram_chat_id=message.from_user.id
    )
    step = user.registration_step

    if user.is_registered or step is None:
        bot.send_message(message.chat.id, "Регистрация прошла успешно!")
        return

    raw = extract_value(message, step)
    ok, validated_or_error = step.validate_data(raw)
    
    if not ok:
        bot.send_message(message.chat.id, validated_or_error, parse_mode='HTML')
        return

    with transaction.atomic():
        step.save_to_user(user, validated_or_error)

        next_step = step.next_step
        user.registration_step = next_step

        if next_step is None:
            user.is_registered = True
        user.save(update_fields=['registration_step', 'is_registered'])

    if user.is_registered:
        bot.send_message(
            message.chat.id, 
            "Регистрация прошла успешно! Осталось только внести организационный взнос. Чтобы это сделать, следуйте по чеку ниже."
        )
        send_invoice(message)
    else:
        markup = generate_phone_markup(user.registration_step)
        bot.send_message(
            message.chat.id,
            user.registration_step.message_text,
            parse_mode='HTML',
            reply_markup=markup
        )


def generate_phone_markup(registration_step: RegistrationStep) -> types.ReplyKeyboardMarkup | None:
    """Создает клавиатуру с кнопкой «Отправить номер», если для выполнения шага требуется номер телефона."""
    if registration_step.field_type == 'phone':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        markup.add(types.KeyboardButton(text='Отправить номер', request_contact=True))
        return markup
    return None


@bot.callback_query_handler(func=lambda call: call.data == "register")
def registration_entry(call: types.CallbackQuery):
    """Точка входа в процесс регистрации."""
    chat_id = call.message.chat.id
    config = Configuration.objects.get_config()

    is_open, msg = is_registration_open(config)
    if not is_open:
        bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
        return

    user, created = User.objects.get_or_create(
        telegram_chat_id=chat_id,
        defaults={'username': call.from_user.username or f'guest_{chat_id}'}
    )
    
    if created:
        logger.info(f"New user created: {chat_id} (@{user.username})")

    if user.is_registered:
        if not user.paid:
            bot.send_message(
                chat_id=chat_id,
                text="Регистрация прошла успешно! Осталось только внести организационный взнос. Чтобы это сделать, следуйте по чеку ниже.",
            )
            send_invoice(call.message)
            return

        bot.send_message(
            chat_id=chat_id,
            text=config.already_registered_message,
            parse_mode='HTML'
        )
        return

    registration_step = RegistrationStep.objects.order_by('order').first()

    if not registration_step:
        logger.warning("Registration entry failed: No registration steps configured.")
        bot.send_message(
            chat_id=chat_id,
            text=config.closed_registrations_message
        )
        return

    user.registration_step = registration_step
    user.save(update_fields=['registration_step'])

    markup = generate_phone_markup(user.registration_step)
    bot.send_message(
        chat_id=chat_id,
        text=registration_step.message_text,
        parse_mode='HTML',
        reply_markup=markup
    )
