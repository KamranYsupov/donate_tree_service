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




