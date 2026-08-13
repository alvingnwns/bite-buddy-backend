from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurasi aplikasi yang dibaca dari environment variables.

    Semua nilai dibaca dari file .env di root project.
    Gunakan lru_cache via get_settings() agar tidak dibaca ulang setiap request.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "BiteBuddy API"
    app_version: str = "0.1.0"
    debug: bool = False
    cors_origins: str = "*"

    # ── Supabase ──────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # ── Gemini AI (Google AI Studio) ──────────
    # Satu API key, beberapa model untuk task berbeda.
    # Model default bisa diubah di .env tanpa ganti kode.
    gemini_api_key: str = ""
    gemini_food_model: str = "gemini-3.5-flash"       # Untuk deteksi makanan dari foto
    gemini_medicine_model: str = "gemini-3.5-flash"   # Untuk deteksi obat/insulin dari foto
    gemini_nutrition_model: str = "gemini-3.5-flash"  # Untuk estimasi kalori & makronutrien

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_mode(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"development", "debug", "dev"}:
                return True
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
