from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/spctek_ai"
    )
    CORS_ORIGINS: str = "http://localhost:3000"
    GOOGLE_API_KEY: str = ""

    # Email configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    FROM_NAME: str = "SPCTEK AI"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
