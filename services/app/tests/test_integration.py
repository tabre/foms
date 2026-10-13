"""Integration tests against PostgreSQL; skipped when the data store is unreachable."""
from decimal import Decimal

from src import errors as E
from src.controllers import alert_controller, filament_controller, order_controller, product_controller
from src.models import Filament, Order, Product


def test_case_insensitive_duplicate_rejected(pg_session):
    cleaned = {"brand": "Elegoo", "type": "PLA", "modifier": "", "color": "White",
             "weight": Decimal("100"), "threshold": Decimal("0")}
    _id, err = filament_controller.add(pg_session, cleaned)
    assert err is None
    _, err = filament_controller.add(pg_session, {**cleaned, "color": "white"})
    assert err == E.filament_exists()


def test_br11_alert_raise_and_clear(pg_session):
    f = Filament(brand="", type="PLA", modifier="", color="Green",
                 weight_available_g=Decimal("10"), low_stock_threshold_g=Decimal("20"))
    pg_session.add(f)
    pg_session.commit()
    alert_controller.evaluate(pg_session, "filament", f)
    alerts = alert_controller.list_alerts(pg_session)
    assert any(a["item"].id == f.id for a in alerts)

    f.weight_available_g = Decimal("30")
    pg_session.commit()
    alert_controller.evaluate(pg_session, "filament", f)
    alerts = alert_controller.list_alerts(pg_session)
    assert not any(a["item"].id == f.id for a in alerts)


def test_br11_partial_unique_index_blocks_second_active_alert(pg_session):
    f = Filament(brand="", type="PLA", modifier="", color="Yellow",
                 weight_available_g=Decimal("1"), low_stock_threshold_g=Decimal("5"))
    pg_session.add(f)
    pg_session.commit()
    alert_controller.evaluate(pg_session, "filament", f)
    alert_controller.evaluate(pg_session, "filament", f)  # must not raise a second active alert
    from sqlalchemy import select
    from src.models import Alert
    n = pg_session.execute(
        select(Alert).where(Alert.item_kind == "filament", Alert.item_id == f.id, Alert.cleared_at.is_(None))
    ).scalars().all()
    assert len(n) == 1


def test_br6_completion_requires_enough_filament(pg_session):
    f = Filament(brand="", type="PLA", modifier="", color="Red",
                  weight_available_g=Decimal("50"), low_stock_threshold_g=Decimal("0"))
    pg_session.add(f)
    pg_session.commit()
    p = Product(name="Cone", default_filament_id=f.id, weight_per_unit_g=Decimal("20"),
               stock_quantity=0, low_stock_threshold=0)
    pg_session.add(p)
    pg_session.commit()
    order = Order(customer_first_name="", customer_last_name="", product_id=p.id,
                  filament_id=f.id, quantity=3, filament_required_g=Decimal("60"),
                  due_date=__import__("datetime").date.today())
    pg_session.add(order)
    pg_session.commit()

    _o, err = order_controller.complete(pg_session, order.id)
    assert err == E.order_needs_more_filament(Decimal("60"), Decimal("50"), f.table_name)
    assert f.weight_available_g == Decimal("50") # nothing changed

    f.weight_available_g = Decimal("60")
    pg_session.commit()
    order, err = order_controller.complete(pg_session, order.id)
    assert err is None
    assert order.complete_date is not None
    assert f.weight_available_g == Decimal("0")

    _o, err = order_controller.complete(pg_session, order.id)
    assert err == E.order_already_completed() #


def test_br8_delete_refusals(pg_session):
    f = Filament(brand="", type="PLA", modifier="", color="Pink",
                 weight_available_g=Decimal("0"), low_stock_threshold_g=Decimal("0"))
    pg_session.add(f)
    pg_session.commit()
    p = Product(name="Spool", default_filament_id=f.id, weight_per_unit_g=Decimal("1"),
               stock_quantity=0, low_stock_threshold=0)
    pg_session.add(p)
    pg_session.commit()
    _ok, err = filament_controller.delete(pg_session, f.id)
    assert err == E.filament_in_use(1)

    order = Order(product_id=p.id, filament_id=f.id, quantity=1, filament_required_g=Decimal("1"),
                 due_date=__import__("datetime").date.today())
    pg_session.add(order)
    pg_session.commit()
    _ok, err = product_controller.delete(pg_session, p.id)
    assert err == E.product_in_use(1)
    _ok, err = order_controller.delete(pg_session, order.id)
    assert err is None
    _ok, err = product_controller.delete(pg_session, p.id)
    assert err is None
