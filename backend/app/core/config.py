from functools import lru_cache
from typing import List

try:
    # Pydantic v2
    from pydantic_settings import BaseSettings, SettingsConfigDict
    class AppSettings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )
except ImportError:
    # Pydantic v1 fallback
    from pydantic import BaseSettings
    class AppSettings(BaseSettings):
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"


class Settings(AppSettings):
    # App
    APP_NAME: str = "ClipViral API"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "clipviral-dev-secret-key-change-in-production"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./clipviral.db"

    # Redis / Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_CELERY: bool = False

    # Storage
    STORAGE_TYPE: str = "local"
    STORAGE_DIR: str = "./storage"

    # AI & LLM Scoring
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-flash"

    # Speech to Text (ASR)
    ASR_PROVIDER: str = "whisper_local"
    WHISPER_MODEL: str = "base"
    OPENAI_WHISPER_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEEPGRAM_API_KEY: str = ""

    # YouTube Direct Publishing
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/youtube/callback"

    # Video Download (yt-dlp)
    YT_DLP_MAX_DURATION_SECONDS: int = 7200
    YT_DLP_STORAGE_PATH: str = "./storage/downloads"

    # Video Render Defaults
    OUTPUT_WIDTH: int = 1080
    OUTPUT_HEIGHT: int = 1920
    OUTPUT_FPS: int = 30
    FONT_FAMILY: str = "Impact"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
