import uuid

from pydantic import BaseModel, Field


class DonateEntity(BaseModel):
    """Представление модели Donate"""

    telegram_user_id: uuid.UUID = Field(title="ID пользователя")
    quantity: float = Field(title="Размер доната")
    is_confirmed: bool = Field(title="Подтвержден", default=False)
    matrix_id: uuid.UUID = Field(title="ID матрицы")


class DonateTransactionEntity(BaseModel):
    sponsor_id: uuid.UUID = Field(title="ID спонсора")
    donate_id: uuid.UUID = Field(title="ID доната")
    is_confirmed: bool = Field(title="Подтвержден", default=False)
    quantity: float = Field(title="Размер доната")
