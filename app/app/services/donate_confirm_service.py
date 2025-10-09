import math
import uuid
from typing import Tuple, Any

import loguru
from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.donate import RepositoryDonate, RepositoryDonateTransaction
from app.models.telegram_user import TelegramUser
from app.schemas.donate import DonateEntity, DonateTransactionEntity
from app.schemas.telegram_user import TelegramUserEntity


class DonateConfirmService:

    def __init__(
        self,
        repository_donate: RepositoryDonate,
        repository_donate_transaction: RepositoryDonateTransaction,
        repository_telegram_user: RepositoryTelegramUser,
    ):
        self._repository_donate = repository_donate
        self._repository_donate_transaction = repository_donate_transaction
        self._repository_telegram_user = repository_telegram_user

    async def create_donate(
        self,
        telegram_user_id: uuid.UUID,
        donate_data: dict,
        matrix_id: uuid.UUID,
        quantity: float,
    ):
        """Создание сущности доната"""
        donate_dict = {
            "telegram_user_id": telegram_user_id,
            "quantity": quantity,
            "matrix_id": matrix_id,
        }
        donate = DonateEntity(**donate_dict)
        donate_obj = self._repository_donate.create(obj_in=donate.model_dump())
        await self._create_donate_transaction(
            donate_id=donate_obj.id, donate_data=donate_data
        )
        return donate_obj

    async def _create_donate_transaction(self, donate_id: uuid.UUID, donate_data: dict):
        """
        Создание конкретной транзакции (часть доната), перечисляемой одному спонсору.
        При создании доната через create_donate - создаются автоматически.
        Всю инфу берет из donate_data.
        """
        for sponsor, sponsor_amount in donate_data.items():
            if sponsor.is_banned:
                sponsor = self._repository_telegram_user.get(is_admin=True)
            donate_transaction_dict = {
                "sponsor_id": sponsor.id,
                "donate_id": donate_id,
                "quantity": sponsor_amount,
            }
            donate_transaction_dict_obj = DonateTransactionEntity(
                **donate_transaction_dict
            )
            self._repository_donate_transaction.create(
                obj_in=donate_transaction_dict_obj.model_dump()
            )

    async def get_donate_by_id(self, donate_id: uuid.UUID):
        """Получить донат по id доната"""
        return self._repository_donate.get(id=donate_id)

    async def get_donate_by_telegram_user_id(self, telegram_user_id: uuid.UUID):
        return self._repository_donate.get_donate_by_telegram_user_id(telegram_user_id)

    async def get_donate_transaction_by_id(self, donate_transaction_id: uuid.UUID):
        """Получить транзакцию по id"""
        return self._repository_donate_transaction.get(id=donate_transaction_id)

    async def get_donate_transaction_by_sponsor_id(self, sponsor_id: uuid.UUID):
        """Получить список транзакций по id спонсора (кому должны перечислить)."""
        return self._repository_donate_transaction.get_donate_transaction_by_sponsor_id(
            sponsor_id
        )

    async def get_all_my_donates_and_transactions(self, telegram_user_id: uuid.UUID):
        """Получить все свои отправленные донаты в виде словаря {донат: транзакции доната}"""
        donates = self._repository_donate.get_donates_list(
            telegram_user_id=telegram_user_id,
        )
        output_dict = {}
        for donate in donates:
            donate_transactions = self._repository_donate_transaction.list(
                donate_id=donate.id
            )
            output_dict[donate] = donate_transactions
        return output_dict

    async def get_donate_transactions_by_donate_id(self, donate_id: uuid.UUID):
        return self._repository_donate_transaction.list(
            donate_id=donate_id, is_confirmed=False
        )

    async def get_all_donates_and_transactions(self):
        """Получить все свои отправленные донаты в виде словаря {донат: транзакции доната}"""
        donates = self._repository_donate.get_donates_list()
        output_dict = {}
        for donate in donates:
            donate_transactions = self._repository_donate_transaction.list(
                donate_id=donate.id
            )
            output_dict[donate] = donate_transactions
        return output_dict

    async def get_all_donate_transactions(self):
        return self._repository_donate_transaction.get_transactions_list()

    async def check_donate_is_confirmed(self, donate_id: uuid.UUID) -> bool:
        """
        Проверка подтвержденности доната.
        Достает все транзакции, проверяет их подтверденность.
        Если все транзакции подтверждены, присваивает donate.is_confirmed True.
        Возвращает булево значение подтверден/не подтвержден весь донат
        """
        donate = await self.get_donate_by_id(donate_id=donate_id)
        donate_transactions = await self.get_donate_transactions_by_donate_id(
            donate_id=donate_id
        )
        is_confirmed_list = []
        for donate_transaction in donate_transactions:
            is_confirmed_list.append(donate_transaction.is_confirmed)
        is_confirmed = math.prod(is_confirmed_list)
        if donate.is_confirmed != is_confirmed:
            donate.is_confirmed = bool(is_confirmed)
        return donate.is_confirmed

    async def set_donate_transaction_is_confirmed(
        self, donate_transaction_id: uuid.UUID
    ):
        """Подтверждение перечисления части доната спонсору"""
        donate_transaction = self._repository_donate_transaction.get(
            id=donate_transaction_id
        )
        self._repository_donate_transaction.update(
            obj_id=donate_transaction.id, obj_in={"is_confirmed": True}
        )
        return donate_transaction

    async def delete_donate_with_transactions(self, donate_id: uuid.UUID) -> None:
        return self._repository_donate.delete_donate_with_transactions(
            donate_id=donate_id
        )

    async def cancel_donate_with_transactions(self, donate_id: uuid.UUID) -> None:
        return self._repository_donate.cancel_donate_with_transactions(
            donate_id=donate_id
        )
