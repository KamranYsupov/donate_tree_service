import os
import secrets
from enum import Enum

from pydantic import PostgresDsn, Field, computed_field
from pydantic_settings import BaseSettings


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def field_validator(param, mode):
    pass


class Settings(BaseSettings):
    """Настройки проекта"""

    # region Настройки бота
    bot_token: str = Field(title="Токен бота")
    bot_name: str | None = Field(title="Имя бота", default=None)
    bot_link: str | None = Field(title="Ссылка на бота", default=os.getenv("BOT_LINK"))
    chat_id: int | None = Field(title="ID канала", default=os.getenv("CHAT_ID"))
    chat_link: str | None = Field(title="Ссылка на канал", default=os.getenv("CHAT_LINK"))
    message_per_second: float = Field(title="Кол-во сообщений в секунду", default=1)
    log_level: LogLevel = Field(title="Уровень логирования", default=LogLevel.INFO)
    # endregion

    debug: bool = Field(title="Режим отладки", default=True)
    secret_key: str = Field(
        title="Секретный ключ", default_factory=lambda: secrets.token_hex(16)
    )

    # region Настройки БД
    postgres_user: str = Field(title="Пользователь БД")
    postgres_password: str = Field(title="Пароль БД")
    postgres_host: str = Field(title="Хост БД")
    postgres_port: int = Field(title="Порт ДБ", default="5432")
    postgres_db: str = Field(title="Название БД")
    # endregion

    # region Настройки RabbitMQ
    rabbitmq_host: str = Field(title="Хост rabbitmq", default="guest:guest@rabbitmq")
    rabbitmq_port: int | str = Field(title="Порт rabbitmq", default=5672)
    # endregion

    # region Настройки Redis
    redis_host: str = Field(title="Хост redis", default="redis")
    redis_port: int | str = Field(title="Порт redis", default=6379)
    # endregion

    # region wallet
    token: str = Field(title="bot token for wallet")
    manifest_url: str = Field(title="contains bot info - link, icon and name")
    bot_wallet_address: str = Field(title="Адрес кошелька бота")
    # endregion

    database_url: PostgresDsn | None = Field(title="Ссылка БД", default=None)

    @computed_field
    @property
    def postgres_url(self) -> PostgresDsn:
        if self.database_url:
            return self.database_url
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=f"{self.postgres_db}",
        )

    @computed_field
    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.rabbitmq_host}:{self.rabbitmq_port}/"

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/"

    @computed_field
    @property
    def celery_broker_url(self) -> str:
        return self.rabbitmq_url

    @computed_field
    @property
    def celery_backend_url(self) -> str:
        return f"{self.redis_url}/0"



class Config:
        env_file = ".env"


settings = Settings()
