from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Application
    app_name: str = Field(default="Fin-Eye Backend", alias="APP_NAME")
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = False
    allowed_origins: list[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/fin_eye",
        alias="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    cache_ttl: int = 900  # 15 minutes

    # External APIs
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    fred_api_key: str = Field(default="", alias="FRED_API_KEY")

    # JWT
    secret_key: str = Field(default="change-in-production", alias="JWT_SECRET")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    require_auth: bool = Field(default=False, alias="REQUIRE_AUTH")

    # Email (CORE-EMAIL-01/02) — Resend integration
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    from_email: str = Field(default="noreply@fin-eye.com", alias="FROM_EMAIL")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # Two-Factor Authentication (TOTP) — CORE-SEC-01
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    totp_encryption_key: str = Field(default="", alias="TOTP_ENCRYPTION_KEY")
    # App name shown in authenticator apps (Google Authenticator, Authy, etc.)
    totp_issuer_name: str = Field(default="Fin-Eye", alias="TOTP_ISSUER_NAME")

    # Model storage (local filesystem for MVP)
    model_store_dir: str = Field(default="model_store", alias="MODEL_STORE_DIR")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

def get_settings() -> Settings:
    return settings
