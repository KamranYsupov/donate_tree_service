from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.services.matrix_service import MatrixService
from app.utils.sponsor import get_callback_value

info_router = Router()


@info_router.message(F.text.casefold() == "baza 🌍")
@inject
async def about_handler(
        message: Message,
) -> None:
    base_photo = FSInputFile("app/media/base_photo.jpg")

    presentation_keyboard = InlineKeyboardBuilder()
    presentation_button = InlineKeyboardButton(
        text="Презентация 📑",
        url="https://telegra.ph/BASE-MLM-PRESENTATION-06-21"
    )
    presentation_keyboard.add(presentation_button)

    await message.answer_photo(
        photo=base_photo,
        caption="МЛМ БАЗА\n\n"
                "Бизнес-клуб, в котором сетевые предприниматели знакомятся, общаются, "
                "обмениваются опытом и отправляют друг другу донаты.",
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


@info_router.message(F.text.casefold() == "реферальная ссылка 🔗")
@inject
async def referral_handler(
        message: Message,
) -> None:
    await message.answer(
        f"Ваша реферальная ссылка: {settings.bot_link}?start={message.from_user.id}",
    )
