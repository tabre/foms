"""Product business rules."""
from decimal import Decimal

from sqlalchemy import select

from src import errors as E
from src import validation as V
from src.controllers import alert_controller
from src.models import Alert, Filament, Order, Product, utcnow


def list_products(session):
    """List products ordered by name."""
    rows = session.execute(select(Product)).scalars().all()
    return sorted(rows, key=lambda p: p.name.lower())


def validate_add(form: dict):
    errors = []
    name, errs = V.clean_text(form.get("name"), "Name", True, 80)
    errors += errs
    weight, errs = V.parse_number(form.get("weight"), "Weight per unit (g)", True, min_value=Decimal("0.1"))
    errors += errs
    stock, errs = V.parse_number(form.get("stock"), "Starting stock (units)", True, whole=True)
    errors += errs
    threshold, errs = V.parse_number(form.get("threshold"), "Low-stock threshold (units)", True, whole=True)
    errors += errs
    return {"name": name, "filament_id": form.get("filament_id"), "weight": weight,
            "stock": stock, "threshold": threshold}, errors


def validate_edit(form: dict):
    """The edit form carries descriptive fields and the threshold only; stock
    changes only through the adjust operation, so it is not required here."""
    errors = []
    name, errs = V.clean_text(form.get("name"), "Name", True, 80)
    errors += errs
    weight, errs = V.parse_number(form.get("weight"), "Weight per unit (g)", True, min_value=Decimal("0.1"))
    errors += errs
    threshold, errs = V.parse_number(form.get("threshold"), "Low-stock threshold (units)", True, whole=True)
    errors += errs
    return {"name": name, "filament_id": form.get("filament_id"), "weight": weight,
            "threshold": threshold}, errors


def add(session, cleaned):
    """Returns (id, error)."""
    if session.execute(select(Product).where(Product.name.ilike(cleaned["name"]))).first():
        return None, E.product_name_exists()
    filament = session.get(Filament, int(cleaned["filament_id"] or 0))
    if filament is None:
        return None, E.missing_reference("filament")
    p = Product(
        name=cleaned["name"], default_filament_id=filament.id,
        weight_per_unit_g=cleaned["weight"], stock_quantity=cleaned["stock"],
        low_stock_threshold=cleaned["threshold"],
    )
    session.add(p)
    session.commit()
    alert_controller.evaluate(session, "product", p)
    return p.id, None


def edit(session, product_id, cleaned):
    """Edit descriptive fields and thresholds. Amounts change only through the
    adjust operation, and existing orders keep their recorded snapshot."""
    p = session.get(Product, product_id)
    if p is None:
        return None, E.missing_reference("product")
    if session.execute(
        select(Product).where(Product.name.ilike(cleaned["name"]), Product.id != product_id)
    ).first():
        return None, E.product_name_exists()
    filament = session.get(Filament, int(cleaned["filament_id"] or 0))
    if filament is None:
        return None, E.missing_reference("filament")
    p.name = cleaned["name"]
    p.default_filament_id = filament.id
    p.weight_per_unit_g = cleaned["weight"]
    p.low_stock_threshold = cleaned["threshold"]
    p.updated_at = utcnow()
    session.commit()
    alert_controller.evaluate(session, "product", p)
    return p, None


def delete(session, product_id):
    """Delete the product, refusing while any order references it. Deletes the
    item's alerts."""
    p = session.get(Product, product_id)
    if p is None:
        return None, E.missing_reference("product")
    orders = session.execute(select(Order).where(Order.product_id == product_id)).scalars().all()
    if orders:
        return None, E.product_in_use(len(orders))
    for a in session.execute(
        select(Alert).where(Alert.item_kind == "product", Alert.item_id == product_id)
    ).scalars().all():
        session.delete(a)
    session.delete(p)
    session.commit()
    return True, None


def adjust(session, product_id, direction: str, amount):
    """Adjust product stock in whole units of at least 1; a negative result is
    rejected with no change."""
    p = session.get(Product, product_id)
    if p is None:
        return None, E.missing_reference("product")
    amount = int(amount)
    if direction == "increase":
        if not p.increase_stock(amount):
            return None, "Amount must be greater than 0."
    elif direction == "decrease":
        if not p.decrease_stock(amount):
            return None, E.insufficient_stock(p.stock_quantity)
    else:
        return None, "Direction must be increase or decrease."
    p.updated_at = utcnow()
    session.commit()
    alert_controller.evaluate(session, "product", p)
    return p, None
