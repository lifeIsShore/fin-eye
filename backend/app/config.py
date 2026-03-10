from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Resolve .env relative to THIS file (backend/app/config.py → backend/.env)
# This ensures the correct .env is loaded regardless of which directory
# the process is launched from.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # Application
    app_name: str = Field(default="Fin-Eye Backend", alias="APP_NAME")
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    allowed_origins: list[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/fin_eye",
        alias="DATABASE_URL",
    )
    async_database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/fin_eye",
        alias="ASYNC_DATABASE_URL",
    )

    # Redis
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    cache_ttl: int = Field(default=900, alias="CACHE_TTL")  # 15 minutes

    # ── Market Data APIs ──────────────────────────────────────────────────────
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    alpha_vantage_api_key: str = Field(default="", alias="ALPHA_VANTAGE_API_KEY")
    polygon_api_key: str = Field(default="", alias="POLYGON_API_KEY")
    tiingo_api_key: str = Field(default="", alias="TIINGO_API_KEY")
    nasdaq_data_link_api_key: str = Field(default="", alias="NASDAQ_DATA_LINK_API_KEY")

    # ── Macro / Economic ──────────────────────────────────────────────────────
    fred_api_key: str = Field(default="", alias="FRED_API_KEY")
    bls_api_key: str = Field(default="", alias="BLS_API_KEY")

    # ── Crypto ────────────────────────────────────────────────────────────────
    coingecko_api_key: str = Field(default="", alias="COINGECKO_API_KEY")
    coinmarketcap_api_key: str = Field(default="", alias="COINMARKETCAP_API_KEY")
    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", alias="BINANCE_API_SECRET")

    # ── News & Sentiment ──────────────────────────────────────────────────────
    newsapi_key: str = Field(default="", alias="NEWSAPI_KEY")
    reddit_client_id: str = Field(default="", alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str = Field(default="", alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(default="fin-eye/1.0", alias="REDDIT_USER_AGENT")
    twitter_bearer_token: str = Field(default="", alias="TWITTER_BEARER_TOKEN")
    benzinga_api_key: str = Field(default="", alias="BENZINGA_API_KEY")

    # ── Forex ─────────────────────────────────────────────────────────────────
    open_exchange_rates_app_id: str = Field(default="", alias="OPEN_EXCHANGE_RATES_APP_ID")
    exchange_rate_api_key: str = Field(default="", alias="EXCHANGE_RATE_API_KEY")
    fixer_api_key: str = Field(default="", alias="FIXER_API_KEY")

    # ── AI / ML ───────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    cohere_api_key: str = Field(default="", alias="COHERE_API_KEY")
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    pinecone_index: str = Field(default="fin-eye-docs", alias="PINECONE_INDEX")
    pinecone_environment: str = Field(default="us-east-1", alias="PINECONE_ENVIRONMENT")

    # ── JWT & Auth ────────────────────────────────────────────────────────────
    secret_key: str = Field(default="change-in-production", alias="JWT_SECRET")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    require_auth: bool = Field(default=False, alias="REQUIRE_AUTH")

    # ── Two-Factor Auth (TOTP) ────────────────────────────────────────────────
    totp_encryption_key: str = Field(default="", alias="TOTP_ENCRYPTION_KEY")
    totp_issuer_name: str = Field(default="Fin-Eye", alias="TOTP_ISSUER_NAME")

    # ── Email — Resend ────────────────────────────────────────────────────────
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    from_email: str = Field(default="noreply@fin-eye.com", alias="FROM_EMAIL")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # ── Payments ──────────────────────────────────────────────────────────────
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(default="", alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id_pro_monthly: str = Field(default="", alias="STRIPE_PRICE_ID_PRO_MONTHLY")
    stripe_price_id_pro_yearly: str = Field(default="", alias="STRIPE_PRICE_ID_PRO_YEARLY")
    stripe_price_id_institutional_monthly: str = Field(default="", alias="STRIPE_PRICE_ID_INSTITUTIONAL_MONTHLY")
    stripe_customer_portal_url: str = Field(default="", alias="STRIPE_CUSTOMER_PORTAL_URL")

    lemonsqueezy_api_key: str = Field(default="", alias="LEMONSQUEEZY_API_KEY")
    lemonsqueezy_store_id: str = Field(default="", alias="LEMONSQUEEZY_STORE_ID")
    lemonsqueezy_webhook_secret: str = Field(default="", alias="LEMONSQUEEZY_WEBHOOK_SECRET")

    paddle_vendor_id: str = Field(default="", alias="PADDLE_VENDOR_ID")
    paddle_api_key: str = Field(default="", alias="PADDLE_API_KEY")
    paddle_webhook_secret: str = Field(default="", alias="PADDLE_WEBHOOK_SECRET")
    paddle_sandbox: bool = Field(default=True, alias="PADDLE_SANDBOX")

    # ── Storage ───────────────────────────────────────────────────────────────
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_s3_bucket: str = Field(default="fin-eye-storage", alias="AWS_S3_BUCKET")
    aws_region: str = Field(default="eu-west-1", alias="AWS_REGION")
    r2_account_id: str = Field(default="", alias="R2_ACCOUNT_ID")
    r2_access_key_id: str = Field(default="", alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str = Field(default="", alias="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="fin-eye-storage", alias="R2_BUCKET")
    r2_endpoint: str = Field(default="", alias="R2_ENDPOINT")

    # ── Error Monitoring ──────────────────────────────────────────────────────
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=0.1, alias="SENTRY_TRACES_SAMPLE_RATE")

    # ── Analytics ─────────────────────────────────────────────────────────────
    posthog_api_key: str = Field(default="", alias="POSTHOG_API_KEY")
    posthog_host: str = Field(default="https://app.posthog.com", alias="POSTHOG_HOST")
    plausible_domain: str = Field(default="", alias="PLAUSIBLE_DOMAIN")

    # ── Notifications ─────────────────────────────────────────────────────────
    slack_ops_webhook_url: str = Field(default="", alias="SLACK_OPS_WEBHOOK_URL")
    slack_error_webhook_url: str = Field(default="", alias="SLACK_ERROR_WEBHOOK_URL")
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    discord_webhook_url: str = Field(default="", alias="DISCORD_WEBHOOK_URL")

    # ── App-Specific ──────────────────────────────────────────────────────────
    model_store_dir: str = Field(default="model_store", alias="MODEL_STORE_DIR")
    backup_dir: str = Field(default="backups", alias="BACKUP_DIR")
    ohlcv_lookback_years: int = Field(default=5, alias="OHLCV_LOOKBACK_YEARS")
    ohlcv_symbols_default: list[str] = Field(
        default=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY", "QQQ", "NVDA"],
        alias="OHLCV_SYMBOLS_DEFAULT",
    )
    rate_limit_anon: int = Field(default=30, alias="RATE_LIMIT_ANON")
    rate_limit_auth: int = Field(default=120, alias="RATE_LIMIT_AUTH")
    rate_limit_api_key: int = Field(default=300, alias="RATE_LIMIT_API_KEY")
    feature_flags: str = Field(default="", alias="FEATURE_FLAGS")

    # ── Helper properties ─────────────────────────────────────────────────────

    @property
    def has_finnhub(self) -> bool:
        return bool(self.finnhub_api_key and self.finnhub_api_key not in ("", "your_key_here"))

    @property
    def has_fred(self) -> bool:
        return bool(self.fred_api_key and self.fred_api_key not in ("", "your_key_here"))

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key not in ("", "your_key_here"))

    @property
    def has_stripe(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_secret_key not in ("", "your_key_here"))

    @property
    def enabled_feature_flags(self) -> list[str]:
        return [f.strip() for f in self.feature_flags.split(",") if f.strip()]

    model_config = SettingsConfigDict(
        # Absolute path — always resolves to backend/.env regardless of CWD
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Ignore extra env vars from .env that aren't fields on this model
        # (e.g. OAuth providers, webhook secrets, payment provider keys, etc.)
        extra="ignore",
    )


settings = Settings()


def get_settings() -> Settings:
    return settings
