"""Configuration. All values are set outside the code and read at startup."""
import os

from pydantic import BaseModel


class Settings(BaseModel):
    # Data-store connection (required)
    pg_host: str
    pg_port: int
    pg_db: str
    pg_user: str
    pg_password: str

    default_timezone: str = "UTC"
    alert_interval_seconds: int = 300
    option_page_size: int = 50
    table_page_size: int = 50
    failed_login_limit: int = 5
    lockout_minutes: int = 15
    session_hours: int = 8
    remember_days: int = 30
    secret: str
    cookie_secure: bool = True # Cookies only over encrypted connections
    session_cookie: str = "foms_session"


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def load_settings() -> Settings:
    secret = _env("FOMS_SECRET")
    if not secret:
        raise RuntimeError("FOMS_SECRET is required")
    return Settings(
        pg_host=_env("PG_IP", "localhost"),
        pg_port=int(_env("PG_PORT", "5432")),
        pg_db=_env("PG_DB", "foms"),
        pg_user=_env("PG_UN", "foms"),
        pg_password=_env("PG_PW", ""),
        default_timezone=_env("FOMS_TZ", "UTC"),
        alert_interval_seconds=int(_env("FOMS_ALERT_INTERVAL", "300")),
        option_page_size=int(_env("FOMS_OPTION_PAGE_SIZE", "50")),
        table_page_size=int(_env("FOMS_TABLE_PAGE_SIZE", "50")),
        failed_login_limit=int(_env("FOMS_FAILED_LOGIN_LIMIT", "5")),
        lockout_minutes=int(_env("FOMS_LOCKOUT_MINUTES", "15")),
        session_hours=int(_env("FOMS_SESSION_HOURS", "8")),
        remember_days=int(_env("FOMS_REMEMBER_DAYS", "30")),
        secret=secret,
        cookie_secure=_env("FOMS_COOKIE_SECURE", "1") not in ("0", "false", "no"),
    )


settings = load_settings()
