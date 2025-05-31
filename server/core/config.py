from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn
from typing import List
from functools import lru_cache

class Settings(BaseSettings):

    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DB_HOST: str
    DB_PORT: int

    KAFKA_HOST: str
    KAFKA_PORT: int
    KAFKA_TOPIC: str

    ORIGINS: List[str] = Field(default_factory=lambda: [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def postgres_dsn(self) -> PostgresDsn:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"

    @property
    def kafka_bootstrap_servers(self) -> str:
        return f"{self.KAFKA_HOST}:{self.KAFKA_PORT}"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
