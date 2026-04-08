from pathlib import Path
from dotenv import load_dotenv
from functools import lru_cache
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    GOOGLE_API_KEY: str
    OPENROUTER_API_KEY: str
    DEPLOY_PASSWORD: str

    # SMTP Settings
    SMTP_PORT: int
    SMTP_HOST: str
    SMTP_USER: str
    SMTP_PASS: str

    class Config:
        env_file = str(BASE_DIR / ".env")
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        print(f"❌ CONFIGURATION ERROR: Missing or invalid environment variables.\n{e}")
        raise SystemExit(1)
