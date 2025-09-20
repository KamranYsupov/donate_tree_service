import uuid

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.telegram_user import TelegramUser, DonateStatus
from .base import RepositoryBase
from app.models.donate import Donate, DonateTransaction


class RepositoryDonate(RepositoryBase[Donate]):
    """Репозиторий доната"""

    def get_donates_list(self):
        statement = select(Donate).order_by(Donate.created_at.desc())

        return self._session.execute(statement).scalars().all()

    def get_donate_by_telegram_user_id(self, telegram_user_id: uuid.UUID):
        statement = (
            select(Donate).filter_by(
                telegram_user_id=telegram_user_id, is_confirmed=False
            )
        ).order_by(Donate.created_at.desc())

        return self._session.execute(statement).scalars().all()

    def delete_donate_with_transactions(self, donate_id: uuid.UUID):
        delete_transactions_statement = (
            delete(DonateTransaction)
            .where(DonateTransaction.donate_id == donate_id)
        )

        delete_donate_statement = (
            delete(Donate)
            .where(Donate.id == donate_id)
        )

        self._session.execute(delete_transactions_statement)
        self._session.execute(delete_donate_statement)



class RepositoryDonateTransaction(RepositoryBase[DonateTransaction]):
    """Репозиторий доната"""

    def get_transactions_list(self):
        statement = select(DonateTransaction).order_by(
            DonateTransaction.created_at.desc()
        )

        return self._session.execute(statement).scalars().all()

    def get_donate_transaction_by_sponsor_id(self, sponsor_id: uuid.UUID):
        statement = (
            select(DonateTransaction)
            .filter_by(sponsor_id=sponsor_id)
            .order_by(DonateTransaction.created_at.desc())
        )

        return self._session.execute(statement).scalars().all()
