"""Server-side validation. Field-level errors name the field."""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from src import errors as E
from src.config import settings
from src.formatting import TZ

USERNAME_RE = re.compile(r"[A-Za-z0-9._-]{3,40}")


def clean_text(value: str | None, field: str, required: bool, max_len: int) -> tuple[str, list]:
    """Trim the value, then check it is present and within the maximum length."""
    value = (value or "").strip()
    errs = []
    if not value:
        if required:
            errs.append({"field": field, "message": E.field_required(field)})
    elif len(value) > max_len:
        errs.append({"field": field, "message": f"{field} must be at most {max_len} characters."})
    return value, errs


def parse_number(value: str | None, field: str, required: bool, *,
                min_value=Decimal("0"), whole=False, max_value=Decimal("1000000"),
                one_decimal=True) -> tuple[Decimal | int | None, list]:
    raw = (value or "").strip()
    errs = []
    if not raw:
        if required:
            return None, [{"field": field, "message": E.field_required(field)}]
        return min_value if not whole else 0, []
    try:
        d = Decimal(raw)
    except InvalidOperation:
        return None, [{"field": field, "message": f"{field} must be a number."}]
    if one_decimal and d.as_tuple().exponent < -1:
        return None, [{"field": field, "message": f"{field} must be a number of 0 or more."}]
    if whole and d != d.to_integral_value():
        return None, [{"field": field, "message": f"{field} must be a whole number of 0 or more."}]
    if d < min_value:
        if min_value == 0:
            msg = f"{field} cannot be negative." if d < 0 else f"{field} must be a number of 0 or more."
        else:
            msg = f"{field} must be at least {min_value} g."
        return None, [{"field": field, "message": msg}]
    if d > max_value:
        return None, [{"field": field, "message": f"{field} must be at most {max_value}."}]
    return d, []


def parse_quantity(value: str | None, field: str) -> tuple[int | None, list]:
    raw = (value or "").strip()
    if not raw:
        return None, [{"field": field, "message": E.field_required(field)}]
    try:
        d = Decimal(raw)
    except InvalidOperation:
        return None, [{"field": field, "message": f"{field} must be a number."}]
    if d != d.to_integral_value() or not (1 <= d <= 9999):
        return None, [{"field": field, "message": "Quantity must be a whole number from 1 to 9999."}]
    return int(d), []


def parse_adjust_amount(value: str | None, field: str, grams: bool) -> tuple[Decimal | int | None, list]:
    raw = (value or "").strip()
    if not raw:
        return None, [{"field": field, "message": E.field_required(field)}]
    try:
        d = Decimal(raw)
    except InvalidOperation:
        return None, [{"field": field, "message": f"{field} must be a number."}]
    if grams:
        if d <= 0:
            return None, [{"field": field, "message": "Amount must be greater than 0."}]
        return d, []
    if d < 1 or d != d.to_integral_value():
        return None, [{"field": field, "message": "Amount must be greater than 0."}]
    return int(d), []


def validate_username(value: str) -> list:
    if not USERNAME_RE.fullmatch(value or ""):
        return [{"field": "Username", "message":
                 "Username must be 3–40 characters: letters, digits, '.', '_' or '-'."}]
    return []


def validate_password(value: str) -> list:
    if not (12 <= len(value or "") <= 128):
        return [{"field": "Password", "message": E.password_length_invalid()}]
    return []


def validate_due_date(value: str | None, field: str) -> tuple[date | None, list]:
    raw = (value or "").strip()
    if not raw:
        return None, [{"field": field, "message": E.field_required(field)}]
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return None, [{"field": field, "message": f"{field} must be a date."}]
    today = datetime.now(TZ).date()
    if d < today:
        return None, [{"field": field, "message": E.due_date_in_past()}]
    return d, []
