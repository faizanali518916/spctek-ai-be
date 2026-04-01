from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv


# Always load .env from the backend root, independent of the current working directory.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/spctek_ai"
    )
    CORS_ORIGINS: str = "http://localhost:3000"
    GOOGLE_API_KEY: str = ""
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # Email configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    FROM_NAME: str = "SPCTEK AI"

    class Config:
        env_file = str(BASE_DIR / ".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
