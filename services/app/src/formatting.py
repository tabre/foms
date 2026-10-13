"""Display formatting."""
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from src.config import settings

TZ = ZoneInfo(settings.default_timezone)


def fmt_grams(value: Decimal) -> str:
    """Grams with one decimal place; trailing zero decimals omitted."""
    d = Decimal(value)
    if d == d.to_integral_value():
        return str(int(d))
    return f"{d:.1f}"


def fmt_units(n: int) -> str:
    return "1 unit" if n == 1 else f"{n} units"


def fmt_amount(kind: str, value) -> str:
    return fmt_grams(value) + " g" if kind == "filament" else fmt_units(value)


def fmt_threshold(kind: str, value) -> str:
    return fmt_grams(value) + " g" if kind == "filament" else fmt_units(value)


def fmt_timestamp(dt: datetime) -> str:
    """Server-side rendering in the configured default timezone.
    Templates wrap this in <time data-utc=...> so the browser can localize."""
    return dt.astimezone(TZ).strftime("%b %-d, %Y %-I:%M %p").lstrip("0")


def fmt_date(d: date) -> str:
    """Dates are shown without timezone conversion."""
    return d.strftime("%b %-d")


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(ZoneInfo("UTC")).isoformat()
