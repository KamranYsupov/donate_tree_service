from datetime import datetime, timedelta
import uuid

import loguru
from aiogram import Router, F, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from aiogram.types import Message

from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.schemas.donate import DonateEntity, DonateTransactionEntity
from app.services.donate_confirm_service import DonateConfirmService
from app.services.telegram_user_service import TelegramUserService
from app.models.telegram_user import status_list
from app.services.donate_service import DonateService
from app.schemas.telegram_user import TelegramUserEntity
from app.keyboards.donate import get_donate_keyboard
from app.utils.sponsor import get_callback_value
from app.models.telegram_user import DonateStatus
from app.core.config import settings
from app.services.matrix_service import MatrixService
from app.schemas.matrix import MatrixEntity
from app.keyboards.donate import get_donations_keyboard
from app.db.commit_decorator import commit_and_close_session
from app.keyboards.reply import get_reply_keyboard
from app.utils.pagination import Paginator
from app.utils.sort import get_reversed_dict
from app.utils.sponsor import check_telegram_user_status
from app.tasks.donate import check_is_donate_confirmed_or_delete_donate_task

donate_router = Router()


@donate_router.callback_query(F.data.startswith("yes_"))
@inject
async def subscribe_handler(
        callback: CallbackQuery,
) -> None:
    sponsor_user_id = get_callback_value(callback.data)

    await callback.message.edit_text(
        f"Для старта работы, подпишитесь на канал нашего сообщества\n\n {settings.chat_link}",
        reply_markup=get_donate_keyboard(
            buttons={
                "Я подписан(а) ✅": f"menu_{sponsor_user_id}",
            }
        ),
    )


@donate_router.callback_query(F.data.startswith("menu_"))
@inject
@commit_and_close_session
async def subscription_checker(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    sponsor_user_id = get_callback_value(callback.data)
    sponsor = await telegram_user_service.get_telegram_user(user_id=sponsor_user_id)

    result = await callback.bot.get_chat_member(
        chat_id=settings.chat_id, user_id=callback.from_user.id
    )
    if result.status not in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        user_dict = callback.from_user.model_dump()
        user_id = user_dict.pop("id")

        user_dict["user_id"] = user_id
        user_dict["sponsor_user_id"] = sponsor_user_id
        user = TelegramUserEntity(**user_dict)

        current_user = await telegram_user_service.create_telegram_user(
            user=user,
            sponsor=sponsor,
        )
        await callback.message.delete()
        await callback.message.answer(
            "✅ Готово! Выбери сервис", reply_markup=get_reply_keyboard(current_user)
        )
        return

    await callback.answer("Ты не подписался ❌", show_alert=True)


@donate_router.message(F.text.casefold() == "донаты 💸")
@inject
async def donations_menu_handler(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    default_buttons = {"Транзакции 💳": "transactions", "МОЯ КОМАНДА": "team_1"}

    current_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )
    if current_user.is_admin:
        message_text = (
            f"Лично приглашенных: <b>{current_user.invites_count}</b>\n"
            f"Получено донатов: <b>{int(current_user.bill)}$</b>\n"
        )
        await message.answer(
            text=message_text,
            reply_markup=get_donate_keyboard(
                buttons=default_buttons,
            ),
        )
        return

    all_donates = await donate_confirm_service.get_donate_by_telegram_user_id(
        telegram_user_id=current_user.id
    )
    buttons = {}
    if not all_donates:
        sponsor = await telegram_user_service.get_telegram_user(
            user_id=current_user.sponsor_user_id
        )
        buttons.update(get_reversed_dict(get_donations_keyboard(current_user, status_list)))
        message_text = (
                f"Ваш спонсор: "
                + ("@" + sponsor.username if sponsor.username else sponsor.first_name)
                + "\n"
                  f"Мой статус: <b>{current_user.status.value}</b>\n"
                  f"Лично приглашенных: <b>{current_user.invites_count}</b>\n"
                  f"Получено донатов: {current_user.bill} <b>$</b>\n"
        )
    else:
        message_text = (
            "Возможность отправки следующего доната будет "
            "доступна только после подтверждения текущего"
        )

    buttons.update(default_buttons)

    await message.answer(
        parse_mode="HTML",
        text=message_text,
        reply_markup=get_donate_keyboard(
            buttons=buttons,
        ),
    )


@donate_router.callback_query(F.data == "donations")
@inject
async def donations_menu_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    default_buttons = {"Транзакции 💳": "transactions", "МОЯ КОМАНДА": "team_1"}

    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    if current_user.is_admin:
        message_text = (
            f"Лично приглашенных: <b>{current_user.invites_count}</b>\n"
            f"Получено донатов: {current_user.bill} <b>$</b>\n"
        )

        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_donate_keyboard(
                buttons=default_buttons,
            ),
        )
        return

    all_donates = await donate_confirm_service.get_donate_by_telegram_user_id(
        telegram_user_id=current_user.id
    )
    buttons = {}
    if not all_donates:
        sponsor = await telegram_user_service.get_telegram_user(
            user_id=current_user.sponsor_user_id
        )
        buttons.update(get_reversed_dict(get_donations_keyboard(current_user, status_list)))
        message_text = (
                f"Ваш спонсор: "
                + ("@" + sponsor.username if sponsor.username else sponsor.first_name)
                + "\n"
                  f"Мой статус: <b>{current_user.status.value}</b>\n"
                  f"Лично приглашенных: <b>{current_user.invites_count}</b>\n"
                  f"Получено донатов: {current_user.bill} <b>$</b>\n"
        )
    else:
        message_text = (
            "Возможность отправки следующего доната будет "
            "доступна только после подтверждения текущего"
        )

    buttons.update(default_buttons | {"МОЯ КОМАНДА": "team_1"})

    await callback.message.edit_text(
        parse_mode="HTML",
        text=message_text,
        reply_markup=get_donate_keyboard(
            buttons=buttons,
        ),
    )


@donate_router.callback_query(F.data.startswith("confirm_donate_"))
@inject
@commit_and_close_session
async def confirm_donate(
        callback: CallbackQuery,
) -> None:
    if "🔴" in callback.data.split("_"):
        return

    callback_donate_data = "_".join(callback.data.split("_")[1:])
    donate_sum = callback_donate_data.split("_")[-1]

    await callback.message.edit_text(
        text=f"Для завершения действия, Вам необходимо отправить донат {donate_sum}$ в течение 15 минут. \n\n"
             "<b>Вы согласны продолжить?</b>",
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": callback_donate_data,
                "Нет": "donations",
            },
            sizes=(2, 1),
        ),
    )


@donate_router.callback_query(F.data.startswith("donate_"))
@inject
@commit_and_close_session
async def donate_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    donate_sum = int(get_callback_value(callback.data))
    status = donate_service.get_donate_status(donate_sum)
    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )

    if not callback.from_user.username:
        await callback.message.edit_text(
            "Перед отправкой доната, добавьте пожалуйста <em>username</em> в свой телеграм аккаунт"
        )
        return

    if callback.from_user.username and current_user.username is None:
        current_user.username = callback.from_user.username

    all_donates = await donate_confirm_service.get_donate_by_telegram_user_id(
        telegram_user_id=current_user.id
    )
    if all_donates:
        message_text = (
            "Возможность отправки следующего доната будет "
            "доступна только после подтверждения текущего"
        )
        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_donate_keyboard(buttons={"МОЯ КОМАНДА": "team_1"}),
        )
        return

    first_sponsor = await telegram_user_service.get_telegram_user(
        user_id=current_user.sponsor_user_id
    )

    donations_data = {}

    matrix = await donate_service.add_user_to_matrix(
        first_sponsor, current_user, donate_sum, donations_data
    )

    donate = await donate_confirm_service.create_donate(
        telegram_user_id=current_user.id,
        donate_data=donations_data,
        matrix_id=matrix.id,
        quantity=donate_sum,
    )

    now = datetime.now()
    eta = now + timedelta(minutes=settings.donate_confirmation_time_minutes)

    check_is_donate_confirmed_or_delete_donate_task.apply_async(
        kwargs={
            "donate_id": donate.id,
            "donate_sender_user_id": current_user.user_id,
    },
        eta=eta
    )
    transactions = await donate_confirm_service.get_donate_transactions_by_donate_id(
        donate_id=donate.id
    )

    message = (
        f"Вы собираетесь отправить донат в размере {donate_sum}$.\n\n"
        f"Для этого свяжитесь с каждым пользователем из списка, "
        f"возьмите их реквизиты, отправьте перевод и запросите подтверждение доната:\n\n"
    )

    for transaction in transactions:
        sponsor = await telegram_user_service.get_telegram_user(
            id=transaction.sponsor_id
        )
        message += f"{int(transaction.quantity)}$ пользователю @{sponsor.username}\n"
        # блок отправки сообщений спонсорам
        try:
            await callback.bot.send_message(
                text=f"Вам донат от @{current_user.username} в размере {int(transaction.quantity)}$\n"
                     f'Нажмите "Подтвердить донат" после получения доната\n',
                chat_id=sponsor.user_id,
                reply_markup=get_donate_keyboard(
                    buttons={"Подтвердить донат": f"first_{transaction.id}"}
                ),
            )
        except Exception:
            pass

    await callback.message.delete()
    await callback.message.answer(message)


@donate_router.callback_query(F.data.startswith("first_"))
@inject
async def first_confirm_handler(
        callback: CallbackQuery,
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    transaction_id = get_callback_value(callback.data)
    transaction = await donate_confirm_service.get_donate_transaction_by_id(
        transaction_id
    )

    if transaction is None:
        await callback.message.edit_text(
            'Время подтверждения транзакции вышло.'
        )
        return

    await callback.message.edit_text(
        text="<b>Вы уверены?</b>",
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"confirm_transaction_{transaction_id}",
                "Нет": f"cancel_confirm_{transaction_id}",
            },
            sizes=(2, 1),
        ),
    )


@donate_router.callback_query(F.data.startswith("firstadmin_"))
@inject
async def first_admin_confirm_handler(callback: CallbackQuery) -> None:
    transaction_id = get_callback_value(callback.data)
    page_number = callback.data.split("_")[-2]

    await callback.message.edit_text(
        text="<b>Вы уверены?</b>",
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"confirm_admin_{transaction_id}",
                "Нет": f"all_transactions_{page_number}",
            },
            sizes=(2, 1),
        ),
    )


@donate_router.callback_query(F.data.startswith("firsttran_"))
@inject
async def first_transactions_confirm_handler(callback: CallbackQuery) -> None:
    transaction_id = get_callback_value(callback.data)
    page_number = callback.data.split("_")[-2]

    await callback.message.edit_text(
        text="<b>Вы уверены?</b>",
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"confirm_transaction_{transaction_id}",
                "Нет": f"transactions_to_me_{page_number}",
            },
            sizes=(2, 1),
        ),
    )


@donate_router.callback_query(F.data.startswith("cancel_confirm_"))
@inject
async def cancel_confirm(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
):
    transaction_id = uuid.UUID(get_callback_value(callback.data))
    transaction = await donate_confirm_service.get_donate_transaction_by_id(transaction_id)

    donate = await donate_confirm_service.get_donate_by_id(
        donate_id=transaction.donate_id
    )
    telegram_user = await telegram_user_service.get_telegram_user(
        id=donate.telegram_user_id
    )

    await callback.message.edit_text(
        text=f"Вам донат от @{telegram_user.username} в размере {int(transaction.quantity)}$\n"
             f'Нажмите "Подтвердить донат" после получения доната\n',
        reply_markup=get_donate_keyboard(
            buttons={"Подтвердить донат": f"first_{transaction.id}"}
        ),
    )


@donate_router.callback_query(F.data == "transactions")
@inject
async def get_transactions_menu(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    buttons = {
        "Транзакции мне 📈": "transactions_to_me_1",
        "Транзакции от меня 📉": "transactions_from_me_1",
    }
    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    if user.is_admin:
        buttons["Все транзакции 📊"] = "all_transactions_1"

    buttons["🔙 Назад"] = "donations"

    await callback.message.edit_text(
        "В этом разделе вы можете посмотреть информацию о подтверждении транзакций по донатам.\n"
        "Выберете раздел:",
        reply_markup=get_donate_keyboard(buttons=buttons),
    )


@donate_router.callback_query(F.data.startswith("transactions_to_me_"))
@inject
@commit_and_close_session
async def get_transactions_list_to_me(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(get_callback_value(callback.data))

    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    transactions = await donate_confirm_service.get_donate_transaction_by_sponsor_id(
        sponsor_id=user.id
    )

    paginator = Paginator(transactions, page_number=page_number, per_page=5)
    buttons = {}
    sizes = (1, 1)

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"transactions_to_me_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"transactions_to_me_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    message = "Транзакции от пользователей Вам.\n\n"
    transactions = paginator.get_page()
    if transactions:
        for transaction in transactions:
            donate = await donate_confirm_service.get_donate_by_id(
                donate_id=transaction.donate_id
            )
            user = await telegram_user_service.get_telegram_user(
                id=donate.telegram_user_id
            )
            message += (
                f"ID: {transaction.id}\n"
                f"Сумма: {int(transaction.quantity)}$\n"
                f"От: @{user.username}\n"
                f"Дата: {transaction.created_at}\n"
            )
            if transaction.is_confirmed:
                message += f"Подтверждена: Да\n\n"
            else:
                message += f"Подтверждена: Нет\n\n"
            if not transaction.is_confirmed:
                buttons[f"Подтвердить {transaction.id}"] = (
                    f"firsttran_{page_number}_{transaction.id}"
                )
    else:
        message = "У вас нет транзакций"

    buttons["🔙 Назад"] = f"transactions"
    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=sizes,
        ),
    )


@donate_router.callback_query(F.data.startswith("transactions_from_me_"))
@inject
async def get_transactions_list_from_me(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(get_callback_value(callback.data))

    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    donates = await donate_confirm_service.get_all_my_donates_and_transactions(
        telegram_user_id=user.id
    )

    paginator = Paginator(list(donates.items()), page_number=page_number, per_page=3)
    buttons = {}
    sizes = (1, 1)
    message = "<b><u>Ваши донаты и транзакции</u></b>\n\n"

    donates = paginator.get_page()
    if donates:
        for donate, transactions in donates:
            message += (
                f"<b><u>Донат на сумму: {int(donate.quantity)}$</u></b>\n"
                f"Дата: {donate.created_at}\n"
            )
            if donate.is_confirmed:
                message += f"Подтвержден: Да\n\n"
            else:
                message += f"Подтвержден: Нет\n\n"

            message += f"<u>Транзакции по донату</u>:\n\n"
            if transactions:
                for transaction in transactions:
                    sponsor = await telegram_user_service.get_telegram_user(
                        id=transaction.sponsor_id
                    )
                    message += (
                        f"ID: {transaction.id}\n"
                        f"Сумма: {int(transaction.quantity)}$\n"
                        f"Кому: @{sponsor.username}\n"
                    )
                    if transaction.is_confirmed:
                        message += f"Подтверждена: Да\n\n"
                    else:
                        message += f"Подтверждена: Нет\n\n"
            else:
                message += "Нет неподтвержденных транзакций по донату.\n\n"
    else:
        message = "У Вас нет неподтвержденных донатов"

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"transactions_from_me_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"transactions_from_me_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    buttons["🔙 Назад"] = f"transactions"

    await callback.message.edit_text(
        message,
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
    )


@donate_router.callback_query(F.data.startswith("all_transactions_"))
@inject
async def get_all_transactions(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(get_callback_value(callback.data))
    donates_and_transactions = (
        await donate_confirm_service.get_all_donates_and_transactions()
    )

    paginator = Paginator(
        list(donates_and_transactions.items()), page_number=page_number, per_page=3
    )
    buttons = {}
    sizes = (1, 1)
    message = "Все донаты и транзакции\n\n"
    donates_and_transactions = paginator.get_page()

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"all_transactions_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"all_transactions_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    if donates_and_transactions:
        for donate, transactions in paginator.get_page():
            user = await telegram_user_service.get_telegram_user(
                id=donate.telegram_user_id
            )
            message += (
                f"<b><u>Донат на сумму: {int(donate.quantity)}$</u></b>\n"
                f"Дата: {donate.created_at}\n"
            )
            if donate.is_confirmed:
                message += f"Подтвержден: Да\n\n"
            else:
                message += f"Подтвержден: Нет\n\n"
            if transactions:
                message += f"<u>Транзакции по донату</u>:\n\n"
                for transaction in transactions:
                    sponsor = await telegram_user_service.get_telegram_user(
                        id=transaction.sponsor_id
                    )
                    message += (
                        f"ID: {transaction.id}\n"
                        f"Сумма: {int(transaction.quantity)}$\n"
                        f"От кого: @{user.username}\n"
                        f"Кому: @{sponsor.username}\n"
                    )
                    if transaction.is_confirmed:
                        message += f"Подтверждена: Да\n\n"
                    else:
                        message += f"Подтверждена: Нет\n\n"
                        buttons[f"Подтвердить {transaction.id}"] = (
                            f"firstadmin_{page_number}_{transaction.id}"
                        )

    buttons["🔙 Назад"] = f"transactions"
    await callback.message.edit_text(
        message,
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=sizes,
        ),
    )


@donate_router.callback_query(F.data.startswith("confirm_transaction_"))
@inject
@commit_and_close_session
async def confirm_transaction(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    transaction_id = uuid.UUID(get_callback_value(callback.data))

    transaction = await donate_confirm_service.get_donate_transaction_by_id(transaction_id)

    donate = await donate_confirm_service.get_donate_by_id(
        donate_id=transaction.donate_id
    )
    if donate.is_confirmed:
        await callback.message.edit_text("Транзакция уже подтверждена")
        return

    transaction = await donate_confirm_service.set_donate_transaction_is_confirmed(
        donate_transaction_id=transaction_id
    )
    sponsor = await telegram_user_service.get_telegram_user(id=transaction.sponsor_id)
    sponsor.bill += transaction.quantity
    sender_user = await telegram_user_service.get_telegram_user(
        id=donate.telegram_user_id
    )
    donate_confirm = await donate_confirm_service.check_donate_is_confirmed(
        donate_id=transaction.donate_id
    )

    if donate_confirm:
        current_matrix_id = donate.matrix_id
        current_matrix = await matrix_service.get_matrix(id=current_matrix_id)

        sender_matrix_dict = {"owner_id": sender_user.id, "status": current_matrix.status}
        sender_matrix_entity = MatrixEntity(**sender_matrix_dict)
        sender_matrix = await matrix_service.create_matrix(matrix=sender_matrix_entity)

        await matrix_service.add_to_matrix(current_matrix, sender_matrix, sender_user)

        if check_telegram_user_status(sender_user, current_matrix.status):
            sender_user.status = current_matrix.status

        try:
            await callback.bot.send_message(
                text=f"Ваш донат успешно подтвержден!\n",
                chat_id=sender_user.user_id,
                reply_markup=get_reply_keyboard(sender_user),
            )
        except Exception:
            pass

    message = (f"Транзакция на сумму {int(transaction.quantity)}"
               f"$ от пользователя @{sender_user.username} подтверждена.")
    await callback.message.edit_text(
        message, reply_markup=get_donate_keyboard(buttons={"🔙 Назад": "transactions"})
    )


@donate_router.callback_query(F.data.startswith("confirm_admin_"))
@inject
@commit_and_close_session
async def confirm_admin_transaction(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    transaction_id = uuid.UUID(callback.data.split("_")[-1])
    transaction = await donate_confirm_service.get_donate_transaction_by_id(transaction_id)

    donate = await donate_confirm_service.get_donate_by_id(
        donate_id=transaction.donate_id
    )
    if donate.is_confirmed:
        await callback.message.edit_text("Транзакция уже подтверждена")
        return

    transaction = await donate_confirm_service.set_donate_transaction_is_confirmed(
        donate_transaction_id=transaction_id
    )
    sponsor = await telegram_user_service.get_telegram_user(id=transaction.sponsor_id)
    sponsor.bill += transaction.quantity
    try:
        if not sponsor.is_admin:
            await callback.bot.send_message(
                text=f"<strong>Транзакция <em>{transaction_id}</em> подтверждена админом</strong>",
                chat_id=sponsor.user_id,
                parse_mode="HTML",
                reply_markup=get_reply_keyboard(sponsor),
            )
    except Exception:
        pass

    sender_user = await telegram_user_service.get_telegram_user(
        id=donate.telegram_user_id
    )
    donate_confirm = await donate_confirm_service.check_donate_is_confirmed(
        donate_id=transaction.donate_id
    )

    if donate_confirm:
        current_matrix_id = donate.matrix_id
        current_matrix = await matrix_service.get_matrix(id=current_matrix_id)

        sender_matrix_dict = {"owner_id": sender_user.id, "status": current_matrix.status}
        sender_matrix_entity = MatrixEntity(**sender_matrix_dict)
        sender_matrix = await matrix_service.create_matrix(matrix=sender_matrix_entity)

        await matrix_service.add_to_matrix(current_matrix, sender_matrix, sender_user)

        if (
                sender_user.status.value == DonateStatus.NOT_ACTIVE.value
                or
                current_matrix.status.get_status_donate_value() >
                sender_user.status.get_status_donate_value()
        ):
            sender_user.status = current_matrix.status

        try:
            await callback.bot.send_message(
                text=f"Ваш донат успешно подтвержден!\n",
                chat_id=sender_user.user_id,
                reply_markup=get_reply_keyboard(sender_user),
            )
        except Exception:
            pass

    message = (f"Транзакция на сумму {int(transaction.quantity)}"
               f"$ от пользователя @{sender_user.username} подтверждена.")
    await callback.message.edit_text(
        message, reply_markup=get_donate_keyboard(buttons={"🔙 Назад": "transactions"})
    )
