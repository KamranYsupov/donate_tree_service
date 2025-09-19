import loguru
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from app.models.telegram_user import TelegramUser
from app.models.telegram_user import DonateStatus


def get_donate_keyboard(*, buttons: dict[str, str], sizes: tuple = (1, 1)):
    keyboard = InlineKeyboardBuilder()

    for text, data in buttons.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()


def get_donations_keyboard(current_user: TelegramUser, status_list) -> dict:
    buttons = {}
    count = 0
    for status in status_list:
        if current_user.status.value == DonateStatus.NOT_ACTIVE.value:
            buttons = {
                "🟢Стартовый - $10🟢": "confirm_donate_🟢_10",
                "🔴Бронза - $30🔴": "confirm_donate_🔴_30",
                "🔴Серебро - $100🔴": "confirm_donate_🔴_100",
                "🔴Золото - $300🔴": "confirm_donate_🔴_300",
                "🔴Платина - $1000🔴": "confirm_donate_🔴_1000",
                "🔴Алмаз - $3000🔴": "confirm_donate_🔴_3000",
                "🔴Бриллиант - $10000🔴": "confirm_donate_🔴_10000",
            }
            break
        elif current_user.status.value == DonateStatus.BRILLIANT.value:
            buttons = {
                "🟢Стартовый - $10🟢": "confirm_donate_🟢_10",
                "🟢Бронза - $30🟢": "confirm_donate_🟢_30",
                "🟢Серебро - $100🟢": "confirm_donate_🟢_100",
                "🟢Золото - $300🟢": "confirm_donate_🟢_300",
                "🟢Платина - $1000🟢": "confirm_donate_🟢_1000",
                "🟢Алмаз - $3000🟢": "confirm_donate_🟢_3000",
                "🟢Бриллиант - $10000🟢": "confirm_donate_🟢_10000",
            }
            break

        if current_user.status.value == status.value:
            for i in status_list[: status_list.index(status)]:
                buttons[f"🟢{i.value}🟢"] = f"confirm_donate_🟢_{i.get_status_donate_value()}"
                count += 1

            buttons[f"🔴{status.value}🔴"] = f"confirm_donate_🔴_{status.get_status_donate_value()}"
            buttons[f"🟢{status_list[count + 1].value}🟢"] = (
                f"confirm_donate_🟢_{status_list[count + 1].get_status_donate_value()}"
            )

            for i in status_list[status_list.index(status) + 2 :]:
                buttons[f"🔴{i.value}🔴"] = f"confirm_donate_🔴_{i.get_status_donate_value()}"
        else:
            continue

    return buttons
