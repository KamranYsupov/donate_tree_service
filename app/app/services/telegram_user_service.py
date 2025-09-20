import uuid
from typing import Tuple, Any

from app.repositories.telegram_user import RepositoryTelegramUser
from app.models.telegram_user import TelegramUser
from app.schemas.telegram_user import TelegramUserEntity
from app.models.matrix import Matrix


class TelegramUserService:

    def __init__(self, repository_telegram_user: RepositoryTelegramUser) -> None:
        self._repository_telegram_user = repository_telegram_user

    async def get_list(self) -> list[TelegramUser]:
        return self._repository_telegram_user.list()

    async def get_telegram_user(self, **kwargs) -> TelegramUser:
        return self._repository_telegram_user.get(**kwargs)

    async def get_sponsors_chain(self, user_id):
        return self._repository_telegram_user.get_sponsors_chain(user_id)

    async def exist(self, **kwargs) -> TelegramUser:
        return self._repository_telegram_user.exists(**kwargs)

    async def get_admin(self) -> TelegramUser:
        return self._repository_telegram_user.get(is_admin=True)

    async def create_telegram_user(
        self,
        user: TelegramUserEntity,
        sponsor: TelegramUser = None,
    ) -> TelegramUser | None:
        user_exist = self._repository_telegram_user.get(user_id=user.user_id)
        if user_exist:
            return user_exist
        if sponsor:
            user.sponsor_user_id = sponsor.user_id
            sponsor.invites_count += 1
        return self._repository_telegram_user.create(obj_in=user.model_dump())

    async def get_telegram_user_sponsors(
        self, user_id: int
    ) -> tuple[TelegramUser, TelegramUser, TelegramUser]:

        return self._repository_telegram_user.get_telegram_user_sponsors(
            user_id=user_id
        )

    async def get_one_sponsor(self, user_id: int):
        return self._repository_telegram_user.get_one_sponsor(user_id=user_id)

    async def delete(self, obj_id: uuid.UUID):
        self._repository_telegram_user.delete(obj_id=obj_id)

    async def get_sponsors_for_separating_donate(self, user_id: int):
        return self._repository_telegram_user.get_sponsors_for_separating_donate(
            user_id=user_id
        )
