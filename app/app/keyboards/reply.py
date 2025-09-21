from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from app.models.telegram_user import TelegramUser, DonateStatus


def get_reply_keyboard(current_user: TelegramUser):
    keyboard = [
        [
            KeyboardButton(text="🎁 GIFT MAFIA 🎁"),
        ],
        [
            KeyboardButton(text="💰 МОИ СТОЛЫ 💰"),
        ]
    ]
    if current_user.status.value != DonateStatus.NOT_ACTIVE.value:
        keyboard.append([KeyboardButton(text="👫 ПРИГЛАСИТЬ ДРУЗЕЙ 👫")])

    reply_keyboard = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    return reply_keyboard
