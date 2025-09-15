from aiogram import Router

from .start import start_router
from .donate import donate_router
from .info import info_router


def get_all_routers() -> Router:
    """Функция для регистрации всех router"""

    router = Router()
    router.include_router(start_router)
    router.include_router(donate_router)
    router.include_router(info_router)

    return router
