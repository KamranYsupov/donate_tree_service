import enum

from sqlalchemy import (
    Column,
    Integer,
    Float,
    ForeignKey,
    Enum,
    UUID,
    Boolean,
    BigInteger,
    UniqueConstraint,
    String,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin, AbstractTelegramUser


class DonateStatus(enum.Enum):
    NOT_ACTIVE = "не активирован"
    BASE = "Стартовый - $10"
    BRONZE = "Бронза - $30"
    SILVER = "Серебро - $100"
    GOLD = "Золото - $300"
    PLATINUM = "Платина - $1000"
    DIAMOND = "Алмаз - $3000"
    BRILLIANT = "Бриллиант - $10000"


status_list = [
    DonateStatus.BASE,
    DonateStatus.BRONZE,
    DonateStatus.SILVER,
    DonateStatus.GOLD,
    DonateStatus.PLATINUM,
    DonateStatus.DIAMOND,
    DonateStatus.BRILLIANT,
]


class TelegramUser(UUIDMixin, TimestampedMixin, AbstractTelegramUser, Base):
    """Модель телеграм пользователя"""

    __tablename__ = "telegram_users"

    status = Column(Enum(DonateStatus), default=DonateStatus.NOT_ACTIVE)
    sponsor_user_id = Column(
        BigInteger,
        ForeignKey("telegram_users.user_id"),
        nullable=True,
        index=True,
    )
    invites_count = Column(Integer, default=0)
    donates_sum = Column(Float, default=0.0)
    bill = Column(Float, default=0.0)
    is_admin = Column(Boolean, index=True, default=False)
    wallet_address = Column(String, nullable=True)

    sponsor = relationship(
        "TelegramUser", remote_side="TelegramUser.user_id", backref="invited_users"
    )
    transactions = relationship("Transaction", back_populates="telegram_user")

    __table_args__ = (
        UniqueConstraint("user_id", name="unique_user_id"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"Пользователь: {self.user_id}"
