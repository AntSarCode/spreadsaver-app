import os
from typing import List, Optional


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    return value if value is not None else default


class Settings:
    # --- App meta ---
    APP_NAME: str = env("APP_NAME", "SpreadSaver")
    ENVIRONMENT: str = env("ENVIRONMENT", "development")

    # --- Auth/JWT ---
    # Prefer SpreadSaver-specific env names with Power6-compatible fallbacks
    SECRET_KEY: str = env("SPREADSAVER_SECRET_KEY", env("SECRET_KEY", "change-me"))
    REFRESH_SECRET_KEY: str = env("SPREADSAVER_REFRESH_SECRET_KEY", env("REFRESH_SECRET_KEY", "change-me-too"))
    ALGORITHM: str = env("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(env("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(env("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # --- Database ---
    # Default to local async Postgres (dev). Override with DATABASE_URL.
    DATABASE_URL: str = env(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5433/postgres",
    )

    # --- CORS ---
    # Comma-separated list or "*"
    ALLOWED_ORIGINS: str = env(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        raw = (self.ALLOWED_ORIGINS or "").strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    # --- Stripe (Phase 6: Monetization) ---
    STRIPE_SECRET_KEY: Optional[str] = env("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = env("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = env("STRIPE_WEBHOOK_SECRET")

    # Success/cancel URLs default to local dev web app
    STRIPE_SUCCESS_URL: str = env(
        "STRIPE_SUCCESS_URL",
        "http://localhost:5173/subscribe?success=1",
    )
    STRIPE_CANCEL_URL: str = env(
        "STRIPE_CANCEL_URL",
        "http://localhost:5173/subscribe?canceled=1",
    )

    # Optional price IDs (not required until products are created)
    STRIPE_PRICE_ID_STARTER_MONTHLY: Optional[str] = env("STRIPE_PRICE_ID_STARTER_MONTHLY")
    STRIPE_PRICE_ID_STARTER_YEARLY: Optional[str] = env("STRIPE_PRICE_ID_STARTER_YEARLY")
    STRIPE_PRICE_ID_PRO_MONTHLY: Optional[str] = env("STRIPE_PRICE_ID_PRO_MONTHLY")
    STRIPE_PRICE_ID_PRO_YEARLY: Optional[str] = env("STRIPE_PRICE_ID_PRO_YEARLY")


settings = Settings()
