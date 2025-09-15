import datetime
import random
from functools import wraps

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from dependency_injector.wiring import inject, Provide
from sqlalchemy.sql import func

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.schemas.telegram_user import TelegramUserEntity
from app.schemas.matrix import MatrixEntity
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.models.telegram_user import status_list
from app.services.matrix_service import MatrixService
from app.utils.sponsor import get_callback_value
from app.services.donate_service import DonateService
from app.models.telegram_user import DonateStatus
from app.db.commit_decorator import commit_and_close_session
from app.keyboards.reply import get_reply_keyboard

from utils.matrix import get_matrices_length

start_router = Router()


@start_router.message(CommandStart())
@inject
async def command_start(
        message: Message,
        command: CommandObject,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    if await telegram_user_service.exist(user_id=message.from_user.id):
        await message.answer(
            f"Вы уже зарегистрированы в системе.\n" f"Продолжить?",
            reply_markup=get_donate_keyboard(
                buttons={
                    "Да": f"menu_1",
                    "Нет": "no",
                },
                sizes=(2, 1),
            ),
        )
        return

    sponsor_user_id = command.args
    sponsor = await telegram_user_service.get_telegram_user(user_id=sponsor_user_id)

    if not sponsor:
        await message.answer("Неправильная ссылка")
        return
    if sponsor.status.value == DonateStatus.NOT_ACTIVE.value:
        await message.answer("Неправильная ссылка")
        return

    await message.answer(
        f"Вы регистрируетесь по рекомендации {sponsor.first_name}"
        f" {sponsor.last_name if sponsor.last_name else ''}"
        f" - Продолжить регистрацию?",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"yes_{sponsor_user_id}",
                "Нет": "no",
            },
            sizes=(2, 1),
        ),
    )


@start_router.callback_query(F.data == "no")
@inject
async def cancel_start_handler(
        callback: CallbackQuery,
) -> None:
    await callback.message.delete()


@start_router.message(Command("admin"))
@inject
@commit_and_close_session
async def admin(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
):
    """Создание системного аккаунта для тестов"""
    admin_user = await telegram_user_service.get_telegram_user(is_admin=True)
    if admin_user:
        return

    user_dict = message.from_user.model_dump()
    user_id = user_dict.pop("id")

    user_dict["user_id"] = user_id
    user_dict["is_admin"] = True
    user_dict["status"] = DonateStatus.BASE
    user = TelegramUserEntity(**user_dict)

    admin_user = await telegram_user_service.create_telegram_user(user=user)

    for status in status_list:
        matrix_dict = {"owner_id": admin_user.id, "status": status}
        matrix = MatrixEntity(**matrix_dict)
        await matrix_service.create_matrix(matrix=matrix)

    await message.answer(
        f"✅ Готово - {settings.bot_link}?start={message.from_user.id}",
        reply_markup=get_reply_keyboard(admin_user),
    )

#
# @start_router.message(F.text.startswith("fake_"))
# @inject
# @commit_and_close_session
# async def add_fake_user(
#         message: Message,
#         telegram_user_service: TelegramUserService = Provide[
#             Container.telegram_user_service
#         ],
#         donate_service: DonateService = Provide[Container.donate_service],
#         matrix_service: MatrixService = Provide[Container.matrix_service],
# ):
#     donate_sum = int(get_callback_value(message.text))
#     status = donate_service.get_donate_status(donate_sum)
#
#     current_user = await telegram_user_service.get_telegram_user(
#         user_id=message.from_user.id
#     )
#
#     user = generate_random_user()
#     user.status = status
#     user.sponsor_user_id = current_user.user_id
#
#     fake_user = await telegram_user_service.create_telegram_user(
#         user=user
#     )
#
#     created_matrix_dict = {"owner_id": fake_user.id, "status": status}
#     created_matrix_entity = MatrixEntity(**created_matrix_dict)
#     created_matrix = await matrix_service.create_matrix(matrix=created_matrix_entity)
#
#     current_matrix = await matrix_service.get_matrix(
#         owner_id=current_user.id,
#         status=status,
#     )
#     await matrix_service.add_to_matrix(current_matrix, created_matrix, fake_user)
#
#     await message.answer(
#         f"✅ пользователь {fake_user.username} успешно добавлен в {current_matrix.id}!\n"
#         f"Статус матрицы: <b>{current_matrix.status.value}</b>"
#         f"{settings.bot_link}?start={fake_user.user_id}",
#         parse_mode="HTML",
#     )
#
#
# # Тут функции только для тестов поэтому нет DRY
# @start_router.message(Command("create_admin"))
# @inject
# @commit_and_close_session
# async def create_admin(
#         message: Message,
#         telegram_user_service: TelegramUserService = Provide[
#             Container.telegram_user_service
#         ],
#         matrix_service: MatrixService = Provide[Container.matrix_service],
# ):
#     admin_user = await telegram_user_service.get_telegram_user(is_admin=True)
#     if admin_user:
#         return
#     user = generate_random_user()
#     user.status = DonateStatus.BASE
#     user.is_admin = True
#
#     admin_user = await telegram_user_service.create_telegram_user(user=user)
#
#     for status in status_list:
#         matrix_dict = {"owner_id": admin_user.id, "status": status}
#         matrix = MatrixEntity(**matrix_dict)
#         await matrix_service.create_matrix(matrix=matrix)
#
#     await message.answer(
#         f"✅ Готово - https://t.me/Kamranchik_Bot?start={admin_user.user_id}",
#     )
#
#
# @start_router.message(F.text.startswith("fakeadmin_"))
# @inject
# @commit_and_close_session
# async def add_fake_user(
#         message: Message,
#         telegram_user_service: TelegramUserService = Provide[
#             Container.telegram_user_service
#         ],
#         donate_service: DonateService = Provide[Container.donate_service],
#         matrix_service: MatrixService = Provide[Container.matrix_service],
# ):
#     donate_sum = int(get_callback_value(message.text))
#     status = donate_service.get_donate_status(donate_sum)
#     admin_user = await telegram_user_service.get_telegram_user(
#         is_admin=True,
#     )
#
#     user = generate_random_user()
#     user.status = status
#     user.sponsor_user_id = admin_user.user_id
#
#     fake_user = await telegram_user_service.create_telegram_user(
#         user=user
#     )
#     matrix_dict = {"owner_id": fake_user.id, "status": status}
#     matrix = MatrixEntity(**matrix_dict)
#     created_matrix = await matrix_service.create_matrix(matrix=matrix)
#
#     admin_matrix = await matrix_service.get_matrix(
#         owner_id=admin_user.id,
#         status=status,
#     )
#     await matrix_service.add_to_matrix(admin_matrix, created_matrix, fake_user)
#
#     await message.answer(
#         f"✅ пользователь {fake_user.username} успешно добавлен в {admin_matrix.id}!\n"
#         f"Статус матрицы: <b>{admin_matrix.status.value}</b>"
#         f"{settings.bot_link}?start={fake_user.user_id}",
#         parse_mode="HTML",
#     )


def generate_random_user():
    return TelegramUserEntity(
        user_id=random.randint(1, 1000),
        username=f"user_{random.randint(1, 1000)}",
        first_name=f"User{random.randint(1, 100)}",
        last_name=f"LastName{random.randint(1, 100)}",
    )
