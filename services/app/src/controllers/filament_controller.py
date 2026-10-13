"""Filament business rules."""
from decimal import Decimal

from sqlalchemy import select

from src import errors as E
from src import validation as V
from src.controllers import alert_controller, product_controller
from src.models import Alert, Filament, Order, Product, utcnow


def list_filaments(session):
    """Ordered by type, then label, case-insensitive."""
    rows = session.execute(select(Filament)).scalars().all()
    return sorted(rows, key=lambda f: (f.type.lower(), f.label.lower()))


def find(session, type_: str, color: str, modifier: str):
    """Case-insensitive equality; no match returns empty result."""
    q = select(Filament).where(
        Filament.type.ilike(type_),
        Filament.color.ilike(color),
        Filament.modifier.ilike(modifier or ""),
    )
    return sorted(session.execute(q).scalars().all(), key=lambda f: f.brand.lower())


def validate_add(form: dict):
    errors = []
    brand, errs = V.clean_text(form.get("brand"), "Brand", False, 60)
    errors += errs
    type_, errs = V.clean_text(form.get("type"), "Type", True, 40)
    errors += errs
    modifier, errs = V.clean_text(form.get("modifier"), "Modifier", False, 40)
    errors += errs
    color, errs = V.clean_text(form.get("color"), "Color", True, 40)
    errors += errs
    weight, errs = V.parse_number(form.get("weight"), "Starting weight (g)", True)
    errors += errs
    threshold, errs = V.parse_number(form.get("threshold"), "Low-stock threshold (g)", True)
    errors += errs
    cleaned = {"brand": brand, "type": type_, "modifier": modifier, "color": color,
              "weight": weight, "threshold": threshold}
    return cleaned, errors


def validate_edit(form: dict):
    """The edit form carries descriptive fields and the threshold only; brand
    and weight are not editable, so they are not required here."""
    errors = []
    type_, errs = V.clean_text(form.get("type"), "Type", True, 40)
    errors += errs
    color, errs = V.clean_text(form.get("color"), "Color", True, 40)
    errors += errs
    modifier, errs = V.clean_text(form.get("modifier"), "Modifier", False, 40)
    errors += errs
    threshold, errs = V.parse_number(form.get("threshold"), "Low-stock threshold (g)", True)
    errors += errs
    cleaned = {"type": type_, "modifier": modifier, "color": color,
               "threshold": threshold}
    return cleaned, errors


def _duplicate(session, cleaned, exclude_id=None) -> bool:
    q = select(Filament).where(
        Filament.brand.ilike(cleaned["brand"]),
        Filament.type.ilike(cleaned["type"]),
        Filament.modifier.ilike(cleaned["modifier"]),
        Filament.color.ilike(cleaned["color"]),
    )
    if exclude_id is not None:
        q = q.where(Filament.id != exclude_id)
    return session.execute(q).first() is not None


def add(session, cleaned):
    """Create, then re-evaluate alert. Returns (id, error)."""
    if _duplicate(session, cleaned):
        return None, E.filament_exists()
    f = Filament(
        brand=cleaned["brand"], type=cleaned["type"], modifier=cleaned["modifier"],
        color=cleaned["color"], weight_available_g=cleaned["weight"],
        low_stock_threshold_g=cleaned["threshold"],
    )
    session.add(f)
    session.commit()
    alert_controller.evaluate(session, "filament", f)
    return f.id, None


def edit(session, filament_id, cleaned):
    """Edit descriptive fields and thresholds only; amounts change only through
    the adjust operation."""
    f = session.get(Filament, filament_id)
    if f is None:
        return None, E.missing_reference("filament")
    if _duplicate(session, {**cleaned, "brand": f.brand}, exclude_id=filament_id):
        return None, E.filament_exists()
    f.type, f.modifier, f.color = cleaned["type"], cleaned["modifier"], cleaned["color"]
    f.low_stock_threshold_g = cleaned["threshold"]
    f.updated_at = utcnow()
    session.commit()
    alert_controller.evaluate(session, "filament", f)
    return f, None


def delete(session, filament_id):
    """Delete the filament, refusing while any product or order references it.
    Deletes the item's alerts."""
    f = session.get(Filament, filament_id)
    if f is None:
        return None, E.missing_reference("filament")
    n = (
        session.execute(select(Product).where(Product.default_filament_id == filament_id)).scalars().all()
    )
    m = session.execute(select(Order).where(Order.filament_id == filament_id)).scalars().all()
    count = len(n) + len(m)
    if count:
        return None, E.filament_in_use(count)
    for a in session.execute(
        select(Alert).where(Alert.item_kind == "filament", Alert.item_id == filament_id)
    ).scalars().all():
        session.delete(a)
    session.delete(f)
    session.commit()
    return True, None


def adjust(session, filament_id, direction: str, amount):
    """Increase/decrease; negative result rejected."""
    f = session.get(Filament, filament_id)
    if f is None:
        return None, E.missing_reference("filament")
    amount = Decimal(amount)
    if direction == "increase":
        if not f.increase_amount(amount):
            return None, "Amount must be greater than 0."
    elif direction == "decrease":
        if not f.decrease_amount(amount):
            return None, E.insufficient_filament(f.weight_available_g)
    else:
        return None, "Direction must be increase or decrease."
    f.updated_at = utcnow()
    session.commit()
    alert_controller.evaluate(session, "filament", f)
    return f, None


def check_stock(session):
    """Flow: the controller asks the filament model, then the product controller."""
    filaments = list_filaments(session)
    products = product_controller.list_products(session)
    alerts = alert_controller.list_alerts(session)
    return filaments, products, alerts
