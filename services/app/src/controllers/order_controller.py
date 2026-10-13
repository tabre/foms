"""Order business rules."""
from decimal import Decimal

from sqlalchemy import select

from src import errors as E
from src import validation as V
from src.controllers import alert_controller
from src.models import Filament, Order, Product, utcnow


def validate_create(form: dict):
    errors = []
    product_id = (form.get("product_id") or "").strip()
    filament_id = (form.get("filament_id") or "").strip()
    if not product_id:
        errors.append({"field": "Product", "message": V.E.field_required("Product")})
    if not filament_id:
        errors.append({"field": "Color", "message": V.E.field_required("Color")})
    quantity, errs = V.parse_quantity(form.get("quantity"), "Quantity")
    errors += errs
    due, errs = V.validate_due_date(form.get("due_date"), "Due date")
    errors += errs
    first, errs = V.clean_text(form.get("first_name"), "Customer first name", False, 60)
    errors += errs
    last, errs = V.clean_text(form.get("last_name"), "Customer last name", False, 60)
    errors += errs
    return {"product_id": product_id, "filament_id": filament_id, "quantity": quantity,
            "due_date": due, "first_name": first, "last_name": last}, errors


def create(session, cleaned):
    """Returns (order_number, error)."""
    product = session.get(Product, int(cleaned["product_id"] or 0))
    if product is None:
        return None, E.missing_reference("product")
    filament = session.get(Filament, int(cleaned["filament_id"] or 0))
    if filament is None:
        return None, E.missing_reference("filament")
    order = Order(
        customer_first_name=cleaned["first_name"],
        customer_last_name=cleaned["last_name"],
        product_id=product.id,
        filament_id=filament.id,
        quantity=cleaned["quantity"],
        filament_required_g=Decimal(cleaned["quantity"]) * Decimal(product.weight_per_unit_g),
        order_date=utcnow(),
        due_date=cleaned["due_date"],
        complete_date=None,
    )
    session.add(order)
    session.commit()
    return order.id, None


def list_orders(session, open_page=1, done_page=1):
    """List orders: open ones by due date then id ascending, completed ones by
    completion date descending, one page at a time."""
    from src.config import settings
    size = settings.table_page_size

    open_q = select(Order).where(Order.complete_date.is_(None)).order_by(
        Order.due_date.asc(), Order.id.asc()
    )
    open_total = session.execute(select(Order).where(Order.complete_date.is_(None))).scalars().all()
    open_rows = session.execute(
        open_q.limit(size).offset((open_page - 1) * size)
    ).scalars().all()

    done_total = session.execute(select(Order).where(Order.complete_date.is_not(None))).scalars().all()
    done_rows = session.execute(
        select(Order).where(Order.complete_date.is_not(None)).order_by(
            Order.complete_date.desc()
        ).limit(size).offset((done_page - 1) * size)
    ).scalars().all()

    return {
        "open_rows": open_rows, "open_total": len(open_total), "open_page": open_page,
        "done_rows": done_rows, "done_total": len(done_total), "done_page": done_page,
        "page_size": size,
    }


def complete(session, order_id):
    """Complete an order as one atomic unit: order and filament rows are locked."""
    order = session.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    ).scalar_one_or_none()
    if order is None:
        return None, E.missing_reference("product")
    session.execute(
        select(Filament).where(Filament.id == order.filament_id).with_for_update()
    ).scalar_one_or_none()

    err = order.complete_order(session)
    if err == E.ORDER_ALREADY_COMPLETED:
        session.rollback()
        return None, E.order_already_completed()
    if err == E.INSUFFICIENT_FILAMENT:
        session.rollback()
        return None, E.order_needs_more_filament(order.filament_required_g, order.filament.weight_available_g, order.filament.table_name)
    if err:
        session.rollback()
        return None, err
    session.commit()
    alert_controller.evaluate(session, "filament", order.filament)
    return order, None


def delete(session, order_id):
    """Delete an open order only. Deleting has no effect on stock."""
    order = session.get(Order, order_id)
    if order is None:
        return None, E.missing_reference("product")
    if order.complete_date is not None:
        return None, E.completed_order_undeletable()
    session.delete(order)
    session.commit()
    return True, None
