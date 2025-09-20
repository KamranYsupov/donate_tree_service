import uuid
from datetime import datetime
from typing import Tuple, Any

import loguru
from dependency_injector.wiring import inject

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.matrix import RepositoryMatrix
from app.models.telegram_user import TelegramUser, DonateStatus
from app.models.matrix import Matrix
from app.services.matrix_service import MatrixService
from app.services.telegram_user_service import TelegramUserService
from app.schemas.matrix import MatrixEntity
from app.utils.matrix import get_matrices_length
from app.utils.matrix import find_first_level_matrix_id
from app.utils.sponsor import check_telegram_user_status


class DonateService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
            repository_matrix: RepositoryMatrix,
    ) -> None:
        self._repository_telegram_user = repository_telegram_user
        self._repository_matrix = repository_matrix

    @staticmethod
    def get_donate_status(donate_sum: int) -> DonateStatus:
        if donate_sum == 10:
            return DonateStatus.BASE
        elif donate_sum == 30:
            return DonateStatus.BRONZE
        elif donate_sum == 100:
            return DonateStatus.SILVER
        elif donate_sum == 300:
            return DonateStatus.GOLD
        elif donate_sum == 1000:
            return DonateStatus.PLATINUM
        elif donate_sum == 3000:
            return DonateStatus.DIAMOND
        elif donate_sum == 10000:
            return DonateStatus.BRILLIANT


    @staticmethod
    def _extend_donations_data(data: dict, sponsor: TelegramUser, donate: int | float):
        if data.get(sponsor):
            data[sponsor] += donate
        else:
            data[sponsor] = donate
        return data

    async def _add_user_to_admin_matrix(
            self,
            donate_sum: int | float,
            status: DonateStatus,
            donations_data: dict,
    ) -> Matrix:
        admin = self._repository_telegram_user.get(is_admin=True)
        admin_matrices = self._repository_matrix.get_user_matrices(
            owner_id=admin.id,
            status=status,
        )

        self._extend_donations_data(donations_data, admin, donate_sum)

        for matrix in admin_matrices:
            if get_matrices_length(matrix.matrices) < 12:
                return matrix

        return admin_matrices[-1]

    @inject
    async def _send_donate_to_matrix_owner(
            self,
            matrix: Matrix,
            current_user: TelegramUser,
            first_sponsor: TelegramUser,
            donate_sum: int | float,
            status: DonateStatus,
            donations_data: dict,
    ) -> Matrix:
        if len(matrix.matrices.keys()) >= 3:
            self._extend_donations_data(donations_data, first_sponsor, donate_sum)
            return matrix
        else:
            parent_matrix = self._repository_matrix.get_parent_matrix(
                matrix_id=matrix.id, status=matrix.status
            )

            if not parent_matrix:
                await self._add_user_to_admin_matrix(
                    donate_sum, status, donations_data
                )
                return matrix

            # переделать

            parent_owner = self._repository_telegram_user.get(id=parent_matrix.owner_id)
            self._extend_donations_data(donations_data, parent_owner, donate_sum)

            return matrix

    async def add_user_to_matrix(
            self,
            first_sponsor: TelegramUser,
            current_user: TelegramUser,
            donate_sum: int,
            donations_data: dict,
    ) -> Matrix:
        status = self.get_donate_status(donate_sum)

        first_sponsor_matrices = self._repository_matrix.get_user_matrices(
            owner_id=first_sponsor.id,
            status=status,
        )

        if first_sponsor.is_admin:
            return await self._add_user_to_admin_matrix(
                donate_sum,
                status,
                donations_data,
            )

        for matrix in first_sponsor_matrices:
            if get_matrices_length(matrix.matrices) < 12:
                return await self._send_donate_to_matrix_owner(
                    matrix,
                    current_user,
                    first_sponsor,
                    donate_sum,
                    status,
                    donations_data,
                )

        else:
            return await self._find_free_matrix(
                current_user,
                donate_sum,
                status,
                donations_data,
            )

    @inject
    async def _find_free_matrix(
            self,
            user_to_add: TelegramUser,
            donate_sum: int | float,
            status: DonateStatus,
            donations_data: dict,
    ):
        while True:
            next_sponsor = self._repository_telegram_user.get(
                user_id=user_to_add.sponsor_user_id
            )
            if next_sponsor is None:
                return await self._add_user_to_admin_matrix(
                    donate_sum,
                    status,
                    donations_data,
                )

            if not (int(status.get_status_donate_value())
                    <= int(next_sponsor.status.get_status_donate_value())):
                user_to_add = next_sponsor
                continue

            next_sponsor_matrices = self._repository_matrix.get_user_matrices(
                owner_id=next_sponsor.id, status=status
            )

            for matrix in next_sponsor_matrices:
                if get_matrices_length(matrix.matrices) < 12:
                    await self._send_donate_to_matrix_owner(
                        matrix,
                        user_to_add,
                        next_sponsor,
                        donate_sum,
                        status,
                        donations_data
                    )

                    return matrix
            else:
                user_to_add = next_sponsor
                continue













