import loguru
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from app.models.telegram_user import DonateStatus, MatrixBuildType, TelegramUser


def get_donate_keyboard(*, buttons: dict[str, str], sizes: tuple = (1, 1)):
    keyboard = InlineKeyboardBuilder()

    for text, data in buttons.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()


def get_donations_keyboard(
        current_status: DonateStatus,
        status_list: list[DonateStatus],
        matrix_build_type: MatrixBuildType,
) -> dict:
    build_type_str = "t" if matrix_build_type == MatrixBuildType.TRINARY else "b"
    buttons = {}
    if current_status.value == DonateStatus.NOT_ACTIVE.value:
        first_status = status_list[0]
        first_donate_sum = first_status.get_status_donate_value(matrix_build_type)
        first_button_text = f"🟢{first_status.value} - ${first_donate_sum}🟢"

        buttons[first_button_text] = f"confirm_donate_🟢_{build_type_str}_{first_donate_sum}"
        for status in status_list[1:]:
            donate_sum = status.get_status_donate_value(matrix_build_type)
            buttons[f"🔴{status.value} - ${donate_sum}🔴"] = \
                f"confirm_donate_🔴_{build_type_str}_{donate_sum}"


        return buttons

    if current_status.value == DonateStatus.BRILLIANT.value:
        for status in status_list:
            donate_sum = status.get_status_donate_value(matrix_build_type)
            buttons[f"🟢{status.value} - ${donate_sum}🟢"] = \
                f"confirm_donate_🟢_{build_type_str}_{donate_sum}"

        return buttons

    count = 0
    for status in status_list:
        if current_status.value == status.value:
            for i in status_list[: status_list.index(status)]:
                buttons[f"🟢{i.value} - ${i.get_status_donate_value(matrix_build_type)}🟢"] = \
                    f"confirm_donate_🟢_{build_type_str}_{i.get_status_donate_value(matrix_build_type)}"
                count += 1

            buttons[f"🔴{status.value} - ${status.get_status_donate_value(matrix_build_type)}🔴"] = \
                f"confirm_donate_🔴_{build_type_str}_{status.get_status_donate_value(matrix_build_type)}"

            buttons[(
                f"🟢{status_list[count + 1].value} - "
                f"${status_list[count + 1].get_status_donate_value(matrix_build_type)}🟢"
            )] = (
                f"confirm_donate_🟢_{build_type_str}_"
                f"{status_list[count + 1].get_status_donate_value(matrix_build_type)}"
            )

            for i in status_list[status_list.index(status) + 2 :]:
                buttons[f"🔴{i.value} - ${i.get_status_donate_value(matrix_build_type)}🔴"] = (
                    f"confirm_donate_🔴_{build_type_str}_"
                    f"{i.get_status_donate_value(matrix_build_type)}"
                )
        else:
            continue

    return buttons
