import loguru
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.services.matrix_service import MatrixService
from app.utils.sponsor import get_callback_value
from app.utils.pagination import Paginator

info_router = Router()


@info_router.message(F.text == "🎁 GIFT MAFIA 🎁")
@inject
async def about_handler(
        message: Message,
) -> None:
    base_photo = FSInputFile("app/media/base_photo.jpg")

    presentation_keyboard = InlineKeyboardBuilder()
    presentation_button = InlineKeyboardButton(
        text="Презентация 📑",
        url="https://telegra.ph/Gift-MAFIA-09-17"
    )
    chat_link_button = InlineKeyboardButton(
        text="💬 Чат Gift Mafia",
        url="https://t.me/gift_mafia_chat"
    )
    presentation_keyboard.add(presentation_button)
    presentation_keyboard.add(chat_link_button)

    await message.answer_photo(
        photo=base_photo,
        caption="GiftMafia - сообщество в котором друзья обмениваются \n"
                "денежными подарками и играют в игру Мафия.",
        reply_markup=presentation_keyboard.adjust(1).as_markup(),
    )


@info_router.message(F.text.casefold() == "моя команда")
@inject
async def team_handler(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
) -> None:
    page_number = 1

    current_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )
    matrices = await matrix_service.get_user_matrices(owner_id=current_user.id)

    message, page_number, buttons, sizes = matrix_service.get_my_team_message(
        matrices=matrices, current_user=current_user, page_number=page_number
    )

    await message.answer(
        message,
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        parse_mode="HTML",
    )


@info_router.callback_query(F.data.startswith("team_"))
@inject
async def team_inline_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
) -> None:
    page_number = int(get_callback_value(callback.data))

    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    matrices = await matrix_service.get_user_matrices(owner_id=current_user.id)

    message, page_number, buttons, sizes = matrix_service.get_my_team_message(
        matrices=matrices, current_user=current_user, page_number=page_number
    )

    buttons |= {"🔙 Назад": f"donations"}

    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        parse_mode="HTML",
    )


@info_router.callback_query(F.data == "chain")
@inject
async def chain_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    message = "<b>Цепочка приглашенных ⛓</b>"
    chain = await telegram_user_service.get_sponsors_chain(
        user_id=callback.from_user.id
    )
    # for telegram_user in chain:
    #     message += f"@{telegram_user.usersname}\n\n" if telegram_user.usersname else f"{telegram_user.firstname}\n\n"

    await callback.message.edit_text(
        f"{chain}",
        reply_markup=get_donate_keyboard(buttons={"🔙 Назад": f"team_1"}),
        parse_mode="HTML",
    )


@inject
async def referral_handler(
        from_user_id: int,
        page_number=1,
        per_page=20,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> tuple[str | None, InlineKeyboardMarkup | None]:
    invited_users = await telegram_user_service.get_invited_users(
        sponsor_user_id=from_user_id
    )
    if not invited_users:
        return None, None

    paginator = Paginator(
        invited_users,
        page_number=page_number,
        per_page=per_page
    )
    buttons = {}
    message_text = f"<b>Ваши рефералы (страница {page_number}):</b>\n\n"

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"referrals_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"referrals_{page_number + 1}"}

    start_count = per_page * page_number - per_page + 1
    for user in paginator.get_page():
        message_text += f"{start_count}. @{user.username}\n"
        start_count += 1

    reply_markup = get_donate_keyboard(
        buttons=buttons,
        sizes=(2,)
    )

    return message_text, reply_markup


@info_router.message(F.text == "👫 ПРИГЛАСИТЬ ДРУЗЕЙ 👫")
@inject
async def referral_message_handler(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    current_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )
    if not current_user:
        return

    message_text, reply_markup = await referral_handler(current_user.user_id)

    if message_text:
        await message.answer(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    await message.answer(
        f"Ваша реферальная ссылка: {settings.bot_link}?start={current_user.user_id}",
    )


@info_router.callback_query(F.data.startswith("referrals_"))
@inject
async def referral_callback_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    page_number = int(callback.data.split('_')[-1])
    message_text, reply_markup = await referral_handler(
        callback.from_user.id,
        page_number=page_number
    )

    await callback.message.edit_text(
        text=message_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
