import uuid
from datetime import datetime

import loguru
from app.models.matrix import Matrix
from app.models.telegram_user import TelegramUser


def get_sorted_matrices(matrices, status_list):
    """Возвращает список матриц отфильтрованных по статусу и полю created_at"""
    status_order = {status: index for index, status in enumerate(status_list)}
    return sorted(
        matrices,
        key=lambda x: (status_order.get(x.status, len(status_list)), x.created_at),
    )


def get_matrices_length(matrices) -> int:
    length = 0
    for i in matrices.items():
        length += 1
        length += len(i[-1])

    return length


def get_matrices_list(matrices) -> tuple[list[Matrix], list[Matrix]]:
    first_level_matrices = []
    second_level_matrices = []
    for first_level_matrix in matrices.keys():
        first_level_matrices.append(uuid.UUID(first_level_matrix))

    for first_level_matrix in first_level_matrices:
        for second_level_matrix in matrices[str(first_level_matrix)]:
            second_level_matrices.append(uuid.UUID(second_level_matrix))

    return first_level_matrices, second_level_matrices


def get_my_team_telegram_usernames(
        matrix,
) -> tuple[list, list, int]:
    first_level_usernames = []
    second_level_usernames = []

    first_matrix_usernames = list(matrix.matrix_telegram_usernames.keys())

    sorted_first_level_usernames = sorted(
        first_matrix_usernames, key=lambda x: datetime.strptime(
            f"{x.split()[-2]} {x.split()[-1]}", "%Y-%m-%d %H:%M:%S.%f"
        )
    )

    length = 0
    for i in range(3):

        try:
            first_level_usernames.append(
                sorted_first_level_usernames[i]
            )
            length += 1
        except IndexError:
            first_level_usernames.append(0)

    for first_level_matrix in sorted_first_level_usernames:
        if first_level_matrix == 0:
            second_level_usernames.extend([0, 0, 0])
            continue
        second_list = []
        for second_level_matrix in matrix.matrix_telegram_usernames[first_level_matrix]:
            second_list.append(second_level_matrix.split()[0])
            length += 1

        while len(second_list) < 3:
            second_list.append(0)

        second_level_usernames.extend(second_list)

    lst = []
    for telegram_username in first_level_usernames:
        if telegram_username != 0:
            lst.append(telegram_username.split()[0])
        else:
            lst.append(telegram_username)

    first_level_usernames = lst

    return first_level_usernames, second_level_usernames, length


def find_first_level_matrix_id(
        matrix: Matrix,
        second_level_matrix_id: Matrix.id
) -> Matrix.id | None:
    for first_level_matrix_id, lst in matrix.matrices.items():
        if str(second_level_matrix_id) in lst:
            return uuid.UUID(first_level_matrix_id)

    return None

