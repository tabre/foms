"""User-facing error messages."""
from decimal import Decimal


INVALID_CREDENTIALS = "invalid_credentials"
TOO_MANY_ATTEMPTS = "too_many_attempts"
INSUFFICIENT_FILAMENT = "insufficient_filament"
ORDER_ALREADY_COMPLETED = "order_already_completed"


def _grams(value) -> str:
    """Render a gram amount without trailing zeros (Postgres NUMERIC returns 60.0)."""
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    if d == d.to_integral_value():
        return str(d.quantize(Decimal(1)))
    return str(d.normalize())


def invalid_credentials() -> str:
    return "Invalid username or password."


def too_many_attempts() -> str:
    return "Too many attempts. Try again later."


def field_required(field: str) -> str:
    return f"{field} is required."


def due_date_in_past() -> str:
    return "Due date cannot be in the past."


def filament_exists() -> str:
    return "That filament already exists."


def product_name_exists() -> str:
    return "A product with that name already exists."


def missing_reference(kind: str) -> str:
    return f"The selected {kind} no longer exists."


def no_matching_filament() -> str:
    return "No matching filament found."


def insufficient_filament(available) -> str:
    return f"Not enough filament: only {_grams(available)} g available."


def insufficient_stock(available: int) -> str:
    return f"Not enough stock: only {available} units available."


def order_needs_more_filament(required, available, filament: str) -> str:
    return (
        f"Cannot complete: this order needs {_grams(required)} g but only "
        f"{_grams(available)} g of {filament} is available."
    )


def order_already_completed() -> str:
    return "This order is already completed."


def filament_in_use(n: int) -> str:
    return f"Cannot delete: this filament is used by {n} product(s) or order(s)."


def product_in_use(n: int) -> str:
    return f"Cannot delete: this product has {n} order(s)."


def completed_order_undeletable() -> str:
    return "Completed orders cannot be deleted."


def last_active_user_required() -> str:
    return "At least one active user is required."


def password_length_invalid() -> str:
    return "Password must be 12 to 128 characters."


def passwords_do_not_match() -> str:
    return "Passwords do not match."


def message(code: str) -> str:
    """Resolve an error constant to its message. Passes already-formatted
    messages through unchanged."""
    fixed = {
        INVALID_CREDENTIALS: invalid_credentials(),
        TOO_MANY_ATTEMPTS: too_many_attempts(),
        ORDER_ALREADY_COMPLETED: order_already_completed(),
    }
    return fixed.get(code, code)
