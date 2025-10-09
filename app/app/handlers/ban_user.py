from aiogram import Router, F, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.db.commit_decorator import commit_and_close_session
from app.core.config import settings
from app.keyboards.donate import get_donate_keyboard
from app.utils.pagination import Paginator
from app.utils.texts import get_user_info_message
from app.keyboards.reply import get_reply_keyboard
from app.keyboards.reply import reply_cancel_keyboard

ban_user_router = Router()


class BanUserState(StatesGroup):
    username = State()


@ban_user_router.message(F.text.lower() == 'отмена ❌')
@inject
async def cancel_handler(
        message: Message,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    current_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )

    await message.answer(
        text="Действие отменено",
        reply_markup=get_reply_keyboard(current_user)
    )

    await state.clear()


@ban_user_router.callback_query(F.data == 'ban_user')
async def start_ban_user_context(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BanUserState.username)
    await callback.message.delete()
    await callback.message.answer(
        "Отправьте username пользователя для блокировки",
        reply_markup=reply_cancel_keyboard,
    )


@ban_user_router.message(BanUserState.username, F.text)
@inject
async def process_name(
        message: Message,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    username = message.text
    telegram_user = await telegram_user_service.get_telegram_user(
        username=username
    )
    current_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )
    error_buttons = {
        "Попробовать ещё раз 🔄": "ban_user",
        "🔙 Назад": "donations",
    }
    async def send_error_message(error_message: str):
        await message.answer(
            text=error_message,
            reply_markup=get_reply_keyboard(current_user)
        )
        await message.answer(
            "Выберите действие:",
            reply_markup=get_donate_keyboard(
                buttons=error_buttons,
                sizes=(1, 1),
            )
        )
        await state.clear()

    if not telegram_user:
        await send_error_message("Пользователь не найден.")
        return
    if telegram_user.is_admin:
        await send_error_message("Невозможно заблокировать админа.")
        return
    if telegram_user.is_banned:
        await send_error_message("Пользователь уже заблокирован.")
        return

    message = await message.answer(
        ".",
        reply_markup=get_reply_keyboard(current_user)
    )

    await message.answer(
        text=html.bold("Вы уверены?"),
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"confirm_ban_{telegram_user.user_id}",
                "Нет": "donations",
            },
            sizes=(1, 1)
        )
    )


@ban_user_router.callback_query(F.data.startswith("confirm_ban_"))
@inject
@commit_and_close_session
async def confirm_ban_user_callback_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    telegram_id = int(callback.data.split('_')[-1])
    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=telegram_id
    )
    telegram_user.is_banned = True
    await callback.message.edit_text(
        f"Пользователь @{telegram_user.username} успешно заблокирован ✅.",
    )

    try:
        await callback.bot.send_message(
            chat_id=telegram_user.user_id,
            text=(
                "Ваш аккаунт заблокирован. Для уточнения причины блокировки, "
                f"свяжитесь со службой поддержки. @{settings.support_username}"
            )
        )
    except TelegramBadRequest:
        pass


@ban_user_router.callback_query(F.data.startswith("banned_users_"))
@inject
async def banned_users_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    page_number = int(callback.data.split("_")[-1])
    back_button = {"🔙 Назад": "donations"}

    banned_users = await telegram_user_service.get_list(
        is_banned=True
    )
    if not banned_users:
        await callback.message.edit_text(
            "Список пуст.",
            reply_markup=get_donate_keyboard(
                buttons=back_button
        ))
        return
    paginator = Paginator(
        banned_users,
        page_number=page_number,
        per_page=1
    )
    user = paginator.get_page()[0]
    message = get_user_info_message(user)


    buttons = {"Разбанить 🔓": f"unban_user_{user.user_id}"}
    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"banned_users_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"banned_users_{page_number + 1}"}

    if len(buttons) == 3:
        sizes = (1, 2, 1)
    else:
        sizes = (1, 1, 1)

    buttons.update(back_button)

    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        parse_mode="HTML",
    )


@ban_user_router.callback_query(F.data.startswith("unban_user_"))
@inject
async def unban_user_callback_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    telegram_id = int(callback.data.split('_')[-1])
    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=telegram_id
    )
    if not telegram_user.is_banned:
        await callback.message.edit_text(
            f"Пользователь @{telegram_user.username} уже разблокирован.",
            reply_markup=get_donate_keyboard(
                button={"🔙 Назад": "donations"},
            )
        )
        return

    await callback.message.edit_text(
        text=html.bold("Вы уверенны?"),
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"confirm_unban_{telegram_user.user_id}",
                "Нет": "donations",
            },
            sizes=(1, 1)
        )
    )


@ban_user_router.callback_query(F.data.startswith("confirm_unban_"))
@inject
@commit_and_close_session
async def confirm_гтban_user_callback_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    telegram_id = int(callback.data.split('_')[-1])
    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=telegram_id
    )
    telegram_user.is_banned = False
    await callback.message.edit_text(
        f"Пользователь @{telegram_user.username} успешно разблокирован ✅."
    )

    try:
        await callback.bot.send_message(
            chat_id=telegram_user.user_id,
            text="Ваш аккаунт разблокирован!"
        )
    except TelegramBadRequest:
        pass