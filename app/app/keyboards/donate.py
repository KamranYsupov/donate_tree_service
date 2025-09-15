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
                "🟢Стартовый - 1500🟢": "confirm_donate_🟢_1500",
                "🔴Бронза - 4500🔴": "confirm_donate_🔴_4500",
                "🔴Серебро - 15000🔴": "confirm_donate_🔴_15000",
                "🔴Золото - 45000🔴": "confirm_donate_🔴_45000",
                "🔴Алмаз - 150000🔴": "confirm_donate_🔴_150000",
                "🔴Бриллиант - 450000🔴": "confirm_donate_🔴_450000",
            }
            break
        elif current_user.status.value == DonateStatus.BRILLIANT.value:
            buttons = {
                "🟢Стартовый - 1500🟢": "confirm_donate_🟢_1500",
                "🟢Бронза - 4500🟢": "confirm_donate_🟢_4500",
                "🟢Серебро - 15000🟢": "confirm_donate_🟢_15000",
                "🟢Золото - 45000🟢": "confirm_donate_🟢_45000",
                "🟢Алмаз - 150000🟢": "confirm_donate_🟢_150000",
                "🟢Бриллиант - 450000🟢": "confirm_donate_🟢_450000",
            }
            break

        if current_user.status.value == status.value:
            for i in status_list[: status_list.index(status)]:
                buttons[f"🟢{i.value}🟢"] = f"confirm_donate_🟢_{i.value.split()[-1]}"
                count += 1

            buttons[f"🔴{status.value}🔴"] = f"confirm_donate_🔴_{status.value.split()[-1]}"
            buttons[f"🟢{status_list[count + 1].value}🟢"] = (
                f"confirm_donate_🟢_{status_list[count + 1].value.split()[-1]}"
            )

            for i in status_list[status_list.index(status) + 2 :]:
                buttons[f"🔴{i.value}🔴"] = f"confirm_donate_🔴_{i.value.split()[-1]}"
        else:
            continue

    return buttons
