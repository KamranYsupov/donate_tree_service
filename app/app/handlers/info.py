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
from app.utils.matrix import get_matrices_length
from app.utils.matrix import get_active_matrices, get_archived_matrices
from app.models.telegram_user import status_list, status_emoji_list

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
        url=settings.presentation_link
    )
    chat_link_button = InlineKeyboardButton(
        text="💬 Чат Gift Mafia",
        url=settings.group_link
    )
    donate_channel_link_button = InlineKeyboardButton(
        text="Канал Подарков 🎁",
        url=settings.donates_channel_link
    )
    presentation_keyboard.add(
        presentation_button,
        chat_link_button,
        donate_channel_link_button
    )
    presentation_keyboard.add()

    await message.answer_photo(
        photo=base_photo,
        caption="GiftMafia - сообщество в котором друзья обмениваются \n"
                "денежными подарками и играют в игру Мафия.",
        reply_markup=presentation_keyboard.adjust(1).as_markup(),
    )



@info_router.callback_query(F.data.startswith("team_"))
@info_router.callback_query(F.data.startswith("archive_team_"))
@inject
async def team_inline_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
) -> None:
    is_archive = callback.data.split("_")[0] == "archive"

    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    matrices = await matrix_service.get_user_matrices(
        owner_id=current_user.id
    )
    archived_matrices = get_archived_matrices(matrices)

    if is_archive:
        matrices = archived_matrices
        title_text = "АРХИВ СТОЛОВ:"
        page_number, previous_page_number = \
            map(int, callback.data.split("_")[-2:])
        callback_data_prefix = "archive_team"
        back_button_data = f"team_{previous_page_number}"
    else:
        matrices = get_active_matrices(matrices)
        title_text = "АКТИВНЫЕ СТОЛЫ:"
        page_number = int(callback.data.split("_")[-1])
        previous_page_number = None
        callback_data_prefix = "team"
        back_button_data = "donations"


    message, page_number, buttons, sizes = matrix_service.get_my_team_message(
        matrices=matrices,
        page_number=page_number,
        previous_page_number=previous_page_number,
        callback_data_prefix=callback_data_prefix
    )
    message = f"<b>{title_text}</b>\n\n" + message


    if not is_archive and archived_matrices:
        buttons["АРХИВ СТОЛОВ 🗄"] = f"archive_team_1_{page_number}"

    buttons["🔙 Назад"] = back_button_data

    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
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
    status_emoji_data = {
        status_list[i]: status_emoji_list[i]
        for i in range(len(status_list))
    }

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"referrals_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"referrals_{page_number + 1}"}

    start_count = per_page * page_number - per_page + 1
    for user in paginator.get_page():
        user_status_emoji = status_emoji_data.get(user.status, "🆓",)
        message_text += f"{start_count}. @{user.username}: {user_status_emoji}\n"
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
