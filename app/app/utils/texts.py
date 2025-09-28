from app.models.telegram_user import DonateStatus


def get_donate_confirm_message(
        donate_sum: int,
        donate_status: DonateStatus,
) -> str | None:
    message_template = (
        "💌 Участник получил  🎁 ${sum}\n\n"
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


