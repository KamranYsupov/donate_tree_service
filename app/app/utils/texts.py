from aiogram import html

from app.models.telegram_user import (
    DonateStatus,
    status_list,
    status_emoji_list,
)
from app.models.telegram_user import TelegramUser


def get_donate_confirm_message(
        donate_sum: int,
        donate_status: DonateStatus,
) -> str | None:
    message_template = (
        "💌 Участник получил 🎁 ${sum}\n\n"
        "🛗 Стол: {status}\n\n"
        "😎 GiftMafia - Вместе к целям!"
    )
    statuses_colors = {
        DonateStatus.BASE: "🟢",
        DonateStatus.BRONZE : "🟠",
        DonateStatus.SILVER: "⚪",
        DonateStatus.GOLD: "🟡",
        DonateStatus.PLATINUM: "⚫",
        DonateStatus.DIAMOND: "🔵",
        DonateStatus.BRILLIANT: "🟣",
    }

    if donate_status not in list(statuses_colors.keys()):
        return

    status = (
        f"{statuses_colors.get(donate_status)} - {donate_status.value.split()[0]}"
    )

    return message_template.format(
        sum=int(donate_sum),
        status=status
    )


def get_user_statuses_statistic_message(
        users: list[TelegramUser],
) -> str:
    status_emoji_data = {
        status_list[i]: status_emoji_list[i]
        for i in range(len(status_list))
    }
    statuses_data = {"🆓": 0}
    statuses_data.update({status: 0 for status in status_emoji_list})

    for user in users:
        if user.status == DonateStatus.NOT_ACTIVE:
            statuses_data["🆓"] += 1
            continue

        statuses_data[status_emoji_data[user.status]] += 1

    message = ""

    for status, count in list(statuses_data.items())[::-1]:
        message += f"{status}: {count}\n"

    return message


def get_user_info_message(user: TelegramUser) -> str:
    message = (
        f"ID: {html.bold(user.id)}\n\n"
        f"Telegram ID: {html.bold(user.user_id)}\n"
        f"Username: @{user.username}\n"
        f"Полное имя: {html.bold(user.full_name)}\n"
        f"Дата и время регистрации: "
        + html.bold(user.created_at.strftime("%d.%m.%Y %H:%M"))
    )
    return message






