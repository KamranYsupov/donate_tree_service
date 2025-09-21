import datetime
import uuid
from typing import Tuple, Any

import loguru

from app.models.telegram_user import DonateStatus, status_list
from app.repositories.matrix import RepositoryMatrix
from app.models import Matrix
from app.schemas.matrix import MatrixEntity
from app.utils.matrix import get_sorted_matrices
from app.utils.pagination import Paginator
from app.models.telegram_user import TelegramUser
from app.repositories.telegram_user import RepositoryTelegramUser
from app.utils.matrix import get_matrices_length, get_matrices_list, get_my_team_telegram_usernames
from app.utils.sort import get_sorted_objects_by_ids
from app.utils.matrix import find_first_level_matrix_id


class MatrixService:
    def __init__(
            self,
            repository_matrix: RepositoryMatrix,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        self._repository_matrix = repository_matrix
        self._repository_telegram_user = repository_telegram_user

    async def get_list(self) -> list[Matrix]:
        return self._repository_matrix.list()

    async def get_matrix(self, **kwargs) -> Matrix:
        return self._repository_matrix.get(**kwargs)

    async def get_user_matrices(
            self,
            owner_id: uuid.uuid4,
            status: DonateStatus = None,
    ) -> list[Matrix]:
        return self._repository_matrix.get_user_matrices(
            owner_id=owner_id,
            status=status,
        )

    async def get_parent_matrix(
            self, matrix_id: Matrix.id, status: DonateStatus, return_all: bool = False
    )-> Matrix:
        return self._repository_matrix.get_parent_matrix(
            matrix_id=matrix_id, status=status, return_all=return_all
        )

    async def create_matrix(self, matrix: MatrixEntity) -> Matrix:
        return self._repository_matrix.create(obj_in=matrix.model_dump())

    async def delete(self, obj_id: uuid.UUID):
        self._repository_matrix.delete(obj_id=obj_id)

    def get_matrix_telegram_users(
            self,
            matrix: Matrix
    ) -> tuple[list[TelegramUser], int]:
        first_matrices_ids, second_matrices_ids = get_matrices_list(matrix.matrices)

        matrices_ids = first_matrices_ids + second_matrices_ids

        first_matrices = self._repository_matrix.get_matrices_by_ids_list(first_matrices_ids)
        second_matrices = self._repository_matrix.get_matrices_by_ids_list(second_matrices_ids)
        first_sorted_matrices = sorted(get_sorted_objects_by_ids(first_matrices, first_matrices_ids),
                                       key=lambda x: x.created_at)
        second_sorted_matrices = sorted(get_sorted_objects_by_ids(second_matrices, second_matrices_ids),
                                        key=lambda x: x.created_at)

        telegram_users_ids = [
            matrix.owner_id if matrix else 0 for matrix in (first_sorted_matrices + second_sorted_matrices)
        ]
        telegram_users = self._repository_telegram_user.get_telegram_users_by_user_ids_list(telegram_users_ids)
        sorted_telegram_users = get_sorted_objects_by_ids(telegram_users, telegram_users_ids)

        return sorted_telegram_users, len(first_matrices_ids)

    def get_my_team_message(
            self,
            matrices: list[Matrix],
            current_user: TelegramUser,
            page_number: int,
    ):
        message = f"<b>МОЯ КОМАНДА:</b>\n\n"
        sorted_matrices = get_sorted_matrices(matrices, status_list)
        paginator = Paginator(sorted_matrices, page_number=page_number, per_page=5)
        buttons = {}
        sizes = (1, 1)

        if len(paginator.get_page()):
            matrices = paginator.get_page()

            for matrix in matrices:
                message += (
                    f"<b>Стол {matrix.id.hex[0:5]}: {matrix.status.value}</b>\n\n"
                )

                first_level_usernames, second_level_usernames, length = get_my_team_telegram_usernames(matrix)

                if not any(username != 0 for username in first_level_usernames) \
                        and not any(username != 0 for username in second_level_usernames):
                    message += "Ваша команда пуста\n"
                else:
                    message += f"<b>1 уровень:</b>\n"
                    for index, telegram_username in enumerate(first_level_usernames):
                        message += \
                            f"{index + 1}. " + (f"@{telegram_username}" if telegram_username else "пусто") + "\n"

                    message += f"\n<b>2 уровень:</b>\n"
                    for index, telegram_username in enumerate(second_level_usernames):
                        message += \
                            f"{index + 1}. " + (f"@{telegram_username}" if telegram_username else "пусто") + "\n"

                message += (
                    f"\nВсего участников: <b>{length}</b>\n\n"
                )
        else:
            message += "У вас нет активированных столов"

        if paginator.has_previous():
            buttons |= {"◀ Пред.": f"team_{page_number - 1}"}
        if paginator.has_next():
            buttons |= {"След. ▶": f"team_{page_number + 1}"}

        if len(buttons) == 2:
            sizes = (2, 1)

        return message, page_number, buttons, sizes

    async def add_to_matrix(
            self,
            matrix_to_add: Matrix,
            created_matrix: Matrix,
            current_user
    ) -> None:
        current_time = datetime.datetime.now()
        created_matrix.created_at = current_time

        matrix_owner = self._repository_telegram_user.get(id=matrix_to_add.owner_id)
        if get_matrices_length(matrix_to_add.matrices) == 12 and matrix_owner.is_admin:
            matrix_to_add_dict = {"owner_id": matrix_owner.id, "status": matrix_to_add.status}
            matrix_to_add_entity = MatrixEntity(**matrix_to_add_dict)
            matrix_to_add = self._repository_matrix.create(obj_in=matrix_to_add_entity)
            (matrix_to_add.matrices,
             matrix_to_add.matrix_telegram_usernames,
             matrix_to_add.telegram_users) = {}, {}, []

        matrix_json = {str(created_matrix.id): []}
        matrix_telegram_user_json = {
            f"{current_user.username} {created_matrix.id} {current_time}": []
        }
        if len(matrix_to_add.matrices.keys()) < 3:
            matrix_to_add.telegram_users.append(current_user.user_id)
            matrix_to_add.matrices.update(matrix_json)
            matrix_to_add.matrix_telegram_usernames.update(matrix_telegram_user_json)

            parent_matrix = self._repository_matrix.get_parent_matrix(
                matrix_id=matrix_to_add.id, status=matrix_to_add.status
            )
            if not parent_matrix:
                return
            # переделать
            parent_matrix.matrices[str(matrix_to_add.id)].append(str(created_matrix.id))

            (parent_matrix.matrix_telegram_usernames[
                     f"{matrix_owner.username} {matrix_to_add.id} {matrix_to_add.created_at}"
                 ].append(f"{current_user.username} {created_matrix.id} {current_time}"))

        else:
            first_level_matrices_ids = [
                uuid.UUID(matrix_id) for matrix_id in list(matrix_to_add.matrices.keys())
            ]
            first_level_matrices = self._repository_matrix.get_matrices_by_ids_list(
                first_level_matrices_ids
            )
            sorted_first_level_matrices = sorted(first_level_matrices, key=lambda x: x.created_at)

            for first_level_matrix in sorted_first_level_matrices:
                if len(first_level_matrix.matrices.keys()) < 3:
                    first_level_matrix_owner = self._repository_telegram_user.get(
                        id=first_level_matrix.owner_id
                    )

                    first_level_matrix.matrices.update(matrix_json)
                    first_level_matrix.matrix_telegram_usernames.update(matrix_telegram_user_json)

                    matrix_to_add.telegram_users.append(current_user.user_id)
                    matrix_to_add.matrices[str(first_level_matrix.id)].append(str(created_matrix.id))
                    (matrix_to_add.matrix_telegram_usernames[
                         f"{first_level_matrix_owner.username} {first_level_matrix.id} {first_level_matrix.created_at}"
                     ]
                     .append(f"{current_user.username} {created_matrix.id} {current_time}"))
                    break
