import uuid
from datetime import datetime
from typing import Tuple, Any

import loguru
from dependency_injector.wiring import inject

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.matrix import RepositoryMatrix
from app.models.telegram_user import TelegramUser, DonateStatus, MatrixBuildType
from app.models.matrix import Matrix
from app.services.matrix_service import MatrixService
from app.services.telegram_user_service import TelegramUserService
from app.schemas.matrix import MatrixEntity
from app.utils.matrix import get_matrices_length
from app.utils.matrix import find_first_level_matrix_id


class DonateService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
            repository_matrix: RepositoryMatrix,
    ) -> None:
        self._repository_telegram_user = repository_telegram_user
        self._repository_matrix = repository_matrix

    @staticmethod
    def get_donate_status(
            donate_sum: int,
            matrix_build_type: MatrixBuildType = MatrixBuildType.TRINARY
    ) -> DonateStatus | None:
        donate_status_data: dict[DonateStatus, int] = DonateStatus.get_donate_status_data(
            matrix_build_type
        )

        for status, value in donate_status_data.items():
            if int(value) == int(donate_sum):
                return status

        return None


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
            matrix_build_type: MatrixBuildType,
            level_length: int,
    ) -> Matrix:

        admin = self._repository_telegram_user.get(is_admin=True)
        admin_matrices = self._repository_matrix.get_user_matrices(
            owner_id=admin.id,
            status=status,
            build_type=matrix_build_type,
        )

        self._extend_donations_data(donations_data, admin, donate_sum)

        for matrix in admin_matrices:
            if get_matrices_length(matrix.matrices) < (level_length * level_length) + level_length:
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
            matrix_build_type: MatrixBuildType,
            level_length: int,
    ) -> Matrix:
        if len(matrix.matrices.keys()) >= level_length:
            self._extend_donations_data(donations_data, first_sponsor, donate_sum)
            return matrix
        else:
            parent_matrix = self._repository_matrix.get_parent_matrix(
                matrix_id=matrix.id, status=matrix.status
            )

            if not parent_matrix:
                await self._add_user_to_admin_matrix(
                    donate_sum,
                    status,
                    donations_data,
                    matrix_build_type=matrix_build_type,
                    level_length=level_length
                )
                return matrix

            parent_owner = self._repository_telegram_user.get(id=parent_matrix.owner_id)
            self._extend_donations_data(donations_data, parent_owner, donate_sum)

            return matrix

    async def add_user_to_matrix(
            self,
            first_sponsor: TelegramUser,
            current_user: TelegramUser,
            donate_sum: int,
            status: DonateStatus,
            donations_data: dict,
            matrix_build_type: MatrixBuildType,
    ) -> Matrix:
        level_length = 2 if matrix_build_type == MatrixBuildType.BINARY else 3
        second_level_length = level_length * level_length
        matrix_max_length = second_level_length + level_length

        first_sponsor_matrices = self._repository_matrix.get_user_matrices(
            owner_id=first_sponsor.id,
            status=status,
            build_type=matrix_build_type,
        )

        if first_sponsor.is_admin:
            return await self._add_user_to_admin_matrix(
                donate_sum,
                status,
                donations_data,
                matrix_build_type=matrix_build_type,
                level_length=level_length,
            )

        for matrix in first_sponsor_matrices:
            if get_matrices_length(matrix.matrices) < matrix_max_length:
                return await self._send_donate_to_matrix_owner(
                    matrix,
                    current_user,
                    first_sponsor,
                    donate_sum,
                    status,
                    donations_data,
                    matrix_build_type=matrix_build_type,
                    level_length=level_length,
                )

        else:
            return await self._find_free_matrix(
                current_user,
                donate_sum,
                status,
                donations_data,
                matrix_build_type=matrix_build_type,
                level_length=level_length,
            )

    @inject
    async def _find_free_matrix(
            self,
            user_to_add: TelegramUser,
            donate_sum: int | float,
            status: DonateStatus,
            donations_data: dict,
            matrix_build_type: MatrixBuildType,
            level_length: int,
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
                    matrix_build_type=matrix_build_type,
                    level_length=level_length,
                )

            if next_sponsor.get_status(matrix_build_type) == DonateStatus.NOT_ACTIVE or not (
                int(status.get_status_donate_value()) <= int(
                    next_sponsor.get_status(matrix_build_type)
                    .get_status_donate_value()
                )
            ):
                user_to_add = next_sponsor
                continue

            next_sponsor_matrices = self._repository_matrix.get_user_matrices(
                owner_id=next_sponsor.id,
                status=status,
                build_type=matrix_build_type,
            )

            for matrix in next_sponsor_matrices:
                if get_matrices_length(matrix.matrices) < (level_length * level_length) + level_length:
                    await self._send_donate_to_matrix_owner(
                        matrix,
                        user_to_add,
                        next_sponsor,
                        donate_sum,
                        status,
                        donations_data,
                        matrix_build_type=matrix_build_type,
                        level_length=level_length,
                    )

                    return matrix
            else:
                user_to_add = next_sponsor
                continue













