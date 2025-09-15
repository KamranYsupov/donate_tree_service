import uuid

from sqlalchemy import select, cast, func, BigInteger, any_
from sqlalchemy.dialects.postgresql import JSONB

from app.models.telegram_user import TelegramUser, DonateStatus
from .base import RepositoryBase
from app.models.matrix import Matrix


class RepositoryMatrix(RepositoryBase[Matrix]):
    """Репозиторий матрицы"""

    def get_parent_matrix(
            self, matrix_id: Matrix.id, status: DonateStatus, return_all: bool = False
    ) -> Matrix | list[Matrix]:
        statement = (
            select(Matrix)
            .where(
                (Matrix.status == status)
                & (Matrix.matrices.has_key(str(matrix_id)))
            )
            .order_by(Matrix.created_at)
        )
        if return_all:
            result = self._session.execute(statement).scalars().all()
        else:
            result = self._session.execute(statement).scalars().first()

        return result

    def get_user_matrices(
            self, owner_id: uuid.uuid4, status: DonateStatus = None
    ) -> list[Matrix]:
        if status:
            statement = (
                select(Matrix)
                .filter_by(owner_id=owner_id, status=status)
                .order_by(Matrix.created_at)
            )
        else:
            statement = (
                select(Matrix).filter_by(owner_id=owner_id).order_by(Matrix.created_at)
            )

        return self._session.execute(statement).scalars().all()

    def get_matrices_by_ids_list(self, matrices_ids: list[Matrix.id]) -> list[Matrix]:
        statement = select(Matrix).filter(Matrix.id.in_(matrices_ids))

        return self._session.execute(statement).scalars().all()




