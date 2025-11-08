import loguru
from aiogram import Router, F, html
from aiogram.filters import Command
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
from app.db.commit_decorator import commit_and_close_session
from app.utils.texts import get_my_team_message, get_matrix_info_message
from app.models.telegram_user import MatrixBuildType

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
    web_app_link_button = InlineKeyboardButton(
        text="Знакомства",
        url=settings.web_app_link
    )
    presentation_keyboard.add(
        presentation_button,
        chat_link_button,
        donate_channel_link_button,
        web_app_link_button,
    )
    presentation_keyboard.add()

    await message.answer_photo(
        photo=base_photo,
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
    callback_data_list = callback.data.split("_")
    is_archive = callback_data_list[0] == "archive"

    build_type_str = callback_data_list[-3] if is_archive else callback_data_list[-2]
    build_type = MatrixBuildType.BINARY \
        if build_type_str == "b" else MatrixBuildType.TRINARY


    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    matrices = await matrix_service.get_user_matrices(
        owner_id=current_user.id,
        build_type=build_type,
    )
    archived_matrices = get_archived_matrices(matrices, build_type)

    if is_archive:
        matrices = archived_matrices
        title_text = "АРХИВ СТОЛОВ:"
        page_number, previous_page_number = \
            map(int, callback.data.split("_")[-2:])
        callback_data_prefix = f"archive_team_{build_type_str}"
        back_button_data = f"team_{build_type_str}_{previous_page_number}"
    else:
        matrices = get_active_matrices(matrices, build_type)
        title_text = "АКТИВНЫЕ СТОЛЫ:"
        page_number = int(callback.data.split("_")[-1])
        previous_page_number = None
        callback_data_prefix = f"team_{build_type_str}"
        back_button_data = f"donations_{build_type_str}"


    message, page_number, buttons, sizes = get_my_team_message(
        matrices=matrices,
        page_number=page_number,
        previous_page_number=previous_page_number,
        callback_data_prefix=callback_data_prefix
    )
    message = f"<b>{title_text}</b>\n\n" + message


    if not is_archive and archived_matrices:
        buttons["АРХИВ СТОЛОВ 🗄"] = f"archive_team_{build_type_str}_1_{page_number}"

    buttons["🔙 Назад"] = back_button_data

    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        parse_mode="HTML",
    )


@info_router.callback_query(F.data.startswith("detail_matrix_"))
@inject
async def team_inline_handler(
        callback: CallbackQuery,
        matrix_service: MatrixService = Provide[Container.matrix_service],
) -> None:
    matrix_id = callback.data.split("_")[-1]
    matrix = await matrix_service.get_matrix(
        id=matrix_id
    )

    message_text = get_matrix_info_message(matrix)
    await callback.message.edit_text(text=message_text)



@info_router.message(F.text == "👫 ПРИГЛАСИТЬ ДРУЗЕЙ 👫")
async def referral_message_handler(message: Message):
    await message.answer(
        text="Выберите тип маркетинга:",
        reply_markup=get_donate_keyboard(
            buttons={
                "BINAR": "send_referrals_b",
                "TRINAR": "send_referrals_t",
            },
            sizes=(1, 1)
        )
    )


@inject
async def referral_handler(
        from_user_id: int,
        build_type: MatrixBuildType,
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

    build_type_str = build_type.value[0]

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"referrals_{build_type_str}_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"referrals_{build_type_str}_{page_number + 1}"}

    buttons.update({"Отправить рассылку 📨": f"referral_message_{page_number}"})

    if len(list(buttons.keys())) == 3:
        sizes = (2, 1)
    else:
        sizes = (1, 1)

    start_count = per_page * page_number - per_page + 1
    for user in paginator.get_page():
        user_status_emoji = status_emoji_data.get(user.get_status(build_type), "🆓",)
        message_text += f"{start_count}. @{user.username}: {user_status_emoji}\n"
        start_count += 1

    reply_markup = get_donate_keyboard(
        buttons=buttons,
        sizes=sizes
    )

    return message_text, reply_markup


@info_router.callback_query(F.data.startswith("send_referrals_"))
@inject
async def send_referral_message_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    build_type_str = callback.data.split("_")[-1]
    build_type = MatrixBuildType.BINARY \
        if build_type_str == "b" else MatrixBuildType.TRINARY

    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    if not current_user:
        return

    message_text, reply_markup = await referral_handler(
        from_user_id=current_user.user_id,
        build_type=build_type,
    )

    await callback.message.delete()
    if message_text:
        await callback.message.answer(
            text=message_text,
            reply_markup=reply_markup,
        )

    photo = FSInputFile("app/media/gift_mafia_logo.jpg")
    gift_mafia_keyboard = InlineKeyboardBuilder()
    registration_link = f"{settings.bot_link}?start={current_user.user_id}"
    registration_button = InlineKeyboardButton(
        text="🚀 РЕГИСТРАЦИЯ 🚀",
        url=registration_link
    )
    gift_mafia_keyboard.add(registration_button)
    await callback.message.answer_photo(
        photo=photo,
        caption=html.bold((
            "🔥 Жаркая премьера - ‘’GiftMafia’’\n\n"
            "💰 Супер алгоритм, $129’960 многократно!\n\n"
            "👑 Стань получателем и забери свою долю!\n\n"
            "👥 Играй вместе с друзьями, получай денежные подарки и наслаждайся жизнью!\n\n"
            "🎟️ Старт, всего $10.\n\n"
            f"{registration_link}"
        )),
        reply_markup=gift_mafia_keyboard.as_markup(),
    )
    await callback.message.answer(
        f"Ваша реферальная ссылка: {registration_link}",
    )


@info_router.callback_query(F.data.startswith("referrals_"))
@inject
async def referral_callback_handler(
        callback: CallbackQuery,
) -> None:
    page_number = int(callback.data.split("_")[-1])
    build_type_str = callback.data.split("_")[-2]
    build_type = MatrixBuildType.BINARY \
        if build_type_str == "b" else MatrixBuildType.TRINARY

    message_text, reply_markup = await referral_handler(
        from_user_id=callback.from_user.id,
        build_type=build_type,
        page_number=page_number,
    )

    await callback.message.edit_text(
        text=message_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
