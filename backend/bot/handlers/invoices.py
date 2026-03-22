import os
import logging
from django.utils import timezone
from django.db.models import F
from telebot import types
from django.conf import settings

from bot.models import Configuration
from bot.bot import bot
from users.models import User
from goods.models import Good

logger = logging.getLogger(__name__)


def _handle_registration_payment(user: User, chat_id: int) -> None:
    """Обрабатывает логику после успешной оплаты регистрации."""
    user.paid = True
    user.paid_at = timezone.now()
    user.save(update_fields=['paid', 'paid_at'])

    bot.send_message(
        chat_id,
        "<b>Оплата принята!</b>\nТеперь вы зарегистрированы. За неделю до мероприятия Вам придет напоминание.", 
        parse_mode='HTML'
    )
    logger.info(f"User {user.id} (Chat: {chat_id}) paid for registration.")


def _handle_good_payment(chat_id: int, payload: str) -> None:
    """Обрабатывает логику после успешной оплаты конкретного товара."""
    try:
        # Fixed: payload format is 'good_<id>'
        good_id = int(payload.split('_')[1])
        good = Good.objects.get(id=good_id)

        if good.quantity > 0:
            # Fixed: Prevent Race Conditions using F expression
            good.quantity = F('quantity') - 1
            good.save(update_fields=['quantity'])

        bot.send_message(
            chat_id,
            f"<b>Оплата принята!</b>\nТовар: {good.title}\nМы уже готовим Ваш товар к отправке.",
            parse_mode='HTML'
        )
        logger.info(f"Good ID {good.id} purchased by Chat ID {chat_id}.")
    except (Good.DoesNotExist, IndexError, ValueError) as e:
        logger.error(f"Error processing good payment for payload '{payload}': {e}", exc_info=True)


def send_invoice(message: types.Message) -> None:
    """Выставляет счет за основную регистрацию."""
    config = Configuration.objects.get_config()
    price_amount = int(config.price * 100)
    
    photo_url = f"{settings.BASE_URL.rstrip('/')}{config.invoice_image.url}" if config.invoice_image else None

    bot.send_invoice(
        chat_id=message.chat.id,
        title=config.invoice_title,
        description=config.invoice_description,
        invoice_payload=config.INVOICE_PAYLOAD,
        provider_token=os.getenv('PROVIDER_TOKEN'),
        currency=os.getenv('CURRENCY'),
        prices=[types.LabeledPrice(label=str(config.invoice_label), amount=price_amount)],
        need_email=True,
        send_email_to_provider=True,
        provider_data=config.provider_data,
        photo_url=photo_url,
    )


def send_good_invoice(message: types.Message, good: Good, all_images: list = None) -> None:
    """Выставляет счет за конкретный товар."""
    price_amount = int(good.price * 100)
    try:
        if all_images is not None:
            invoice_images = [img for img in all_images if img.is_invoice]
            invoice_image = invoice_images[0] if invoice_images else None
        else:
            invoice_image = good.images.filter(is_invoice=True).first()

        photo_url = f"{settings.BASE_URL.rstrip('/')}{invoice_image.image.url}" if invoice_image else None

        bot.send_invoice(
            chat_id=message.chat.id,
            title=good.title,
            description=good.label or good.title,
            invoice_payload=f"good_{good.id}",
            provider_token=os.getenv('PROVIDER_TOKEN'),
            currency=os.getenv('CURRENCY'),
            prices=[types.LabeledPrice(label=str(good.label), amount=price_amount)],
            need_email=True,
            send_email_to_provider=True,
            provider_data=good.provider_data,
            photo_url=photo_url,
        )
    except Exception as e:
        logger.error(f"Failed to send good invoice (Good ID: {good.id}): {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка генерации чека. Пожалуйста, попробуйте еще раз.")


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query: types.PreCheckoutQuery):
    """Обрабатывает запросы перед оформлением заказа для проверки наличия товара или статуса пользователя перед оплатой."""
    payload = pre_checkout_query.invoice_payload
    config = Configuration.objects.get_config()

    if payload.startswith('good_'):
        try:
            good_id = int(payload.split('_')[1])
            good = Good.objects.get(id=good_id)
            if good.quantity <= 0 or not good.available:
                return bot.answer_pre_checkout_query(
                    pre_checkout_query.id,
                    ok=False,
                    error_message="Просим прощения, товар только что закончился."
                )
        except Exception:
            logger.warning(f"Invalid checkout attempt for payload: {payload}")
            return bot.answer_pre_checkout_query(
                pre_checkout_query.id, 
                ok=False,
                error_message="Ошибка проверки товара."
            )
            
    elif payload == config.INVOICE_PAYLOAD:
        try:
            chat_id = pre_checkout_query.from_user.id
            user = User.objects.filter(telegram_chat_id=chat_id).first()

            if not user or not user.is_registered:
                return bot.answer_pre_checkout_query(
                    pre_checkout_query.id,
                    ok=False,
                    error_message="Пользователь не найден или не завершена регистрация. Пожалуйста, зарегистрируйтесь."
                )
            if user.paid:
                return bot.answer_pre_checkout_query(
                    pre_checkout_query.id,
                    ok=False,
                    error_message="Вы уже оплатили регистрацию."
                )
            if pre_checkout_query.total_amount / 100 != config.price:
                return bot.answer_pre_checkout_query(
                    pre_checkout_query.id,
                    ok=False,
                    error_message='Цена регистрации поменялась. Пожалуйста, начните процесс регистрации заново (/start для отправки нового чека)'
                )

        except Exception as e:
            logger.error(f"Checkout validation error: {e}", exc_info=True)
            return bot.answer_pre_checkout_query(
                pre_checkout_query.id, 
                ok=False,
                error_message="Ошибка проверки регистрации."
            )

    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def got_payment(message: types.Message):
    """Обрабатывает подтверждения успешных платежей из Telegram."""
    payment = message.successful_payment
    payload = payment.invoice_payload
    chat_id = message.chat.id

    try:
        user = User.objects.get(telegram_chat_id=chat_id)

        if payload == Configuration.objects.get_config().INVOICE_PAYLOAD:
            _handle_registration_payment(user, chat_id)
        elif payload.startswith('good_'):
            _handle_good_payment(chat_id, payload)

    except User.DoesNotExist:
        logger.error(f"Successful payment from unknown user (Chat ID: {chat_id}, Payload: {payload}).")
        bot.send_message(chat_id, "Случилась ошибка: пользователь не найден. Пожалуйста, свяжитесь с менеджером и попробуйте пройти регистрацию заново.")
