from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from app.models.telegram_user import TelegramUser, DonateStatus


def get_reply_keyboard(current_user: TelegramUser):
    keyboard = [
        [
            KeyboardButton(text="🎁 GIFT NETWORK 🎁"),
        ],
        [
            KeyboardButton(text="💰 МОИ СТОЛЫ 💰"),
        ]
    ]
    if (
        current_user.trinary_status != DonateStatus.NOT_ACTIVE
        or current_user.binary_status != DonateStatus.NOT_ACTIVE
    ):
        keyboard.append([KeyboardButton(text="👫 ПРИГЛАСИТЬ ДРУЗЕЙ 👫")])

    reply_keyboard = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    return reply_keyboard


reply_cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отмена ❌")]
    ],
    resize_keyboard=True
)

