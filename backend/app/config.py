from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Application
    app_name: str = Field(default="Fin-Eye Backend", alias="APP_NAME")
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = False

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
    jwt_secret: str = Field(default="change-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"

    # Model storage (local filesystem for MVP)
    model_store_dir: str = Field(default="model_store", alias="MODEL_STORE_DIR")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
