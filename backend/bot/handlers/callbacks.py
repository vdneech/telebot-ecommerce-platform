from bot.models import Configuration
from bot.bot import bot
from telebot import types

_DATA = [
    'ceo',
    'format',
]

def _get_text_for_command(command: str) -> str:
    """Возвращает из базы текст, соответствующий конкретной команде."""
    config = Configuration.objects.get_config()
    field_name = f"{command}_message"
    return getattr(config, field_name)


@bot.message_handler(commands=_DATA)
def command_handler(
    message: types.Message = None,
    callback: types.CallbackQuery = None
) -> None:
    """Обрабатывает входящую команду или обратный вызов и отправляет соответствующее сообщение пользователю."""
    if message:
        command = message.text[1:] if message.text.startswith('/') else message.text
    elif callback:
        command = callback.data
        message = callback.message

    text = _get_text_for_command(command)

    bot.send_message(
        message.chat.id,
        text=text,
        parse_mode="HTML",
    )

@bot.callback_query_handler(func=lambda callback: callback.data in _DATA)
def callback_handler(callback: types.CallbackQuery) -> None:
    """Перенаправляет коллбек обработчику команды."""
    command_handler(callback=callback)