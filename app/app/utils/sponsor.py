from aiogram.types import Message

from app.models.telegram_user import DonateStatus, status_list
from app.keyboards.donate import get_donate_keyboard
from app.models.telegram_user import TelegramUser


def get_callback_value(callback_data: str) -> str:
    callback_value = callback_data.split("_")[-1]
    return callback_value


def check_telegram_user_status(telegram_user: TelegramUser, status: DonateStatus) -> bool:
    expression = (
        telegram_user.status.value == DonateStatus.NOT_ACTIVE.value or
        status.get_status_donate_value() > telegram_user.status.get_status_donate_value()
    )

    return expression


async def send_donations_keyboard(
    message: Message,
    current_status: DonateStatus,
    edit_text: bool = False,
) -> None:
    """Функция для отправки клавиатуры донатов"""
    message_data = dict(
        parse_mode="HTML",
        text=f"Вы не можете выбрать <b>{current_status.value}</b> повторно",
        reply_markup=get_donate_keyboard(buttons={"🔙 Назад": "donations"}),
    )
    if edit_text:
        await message.edit_text(**message_data)
    else:
        await message.answer(**message_data)


