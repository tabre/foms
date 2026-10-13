"""Entity behavior and business rules on pure objects."""
from decimal import Decimal

from src.models import Filament, Order, Product


def filament(**kw):
    base = {"brand": "", "type": "PLA", "modifier": "", "color": "White",
           "weight_available_g": Decimal("100"), "low_stock_threshold_g": Decimal("50")}
    base.update(kw)
    return Filament(**base)


def product(**kw):
    base = {"name": "Cone", "default_filament_id": 1, "weight_per_unit_g": Decimal("20"),
            "stock_quantity": 5, "low_stock_threshold": 2}
    base.update(kw)
    return Product(**base)


def test_br2_strictly_less_than_threshold():
    f = filament(weight_available_g=Decimal("50"))
    assert not f.is_low_stock()  # equal is not low
    f.weight_available_g = Decimal("49.9")
    assert f.is_low_stock()


def test_br2_zero_threshold_never_triggers():
    f = filament(weight_available_g=Decimal("0"), low_stock_threshold_g=Decimal("0"))
    assert not f.is_low_stock()


def test_br3_negative_result_rejected():
    f = filament(weight_available_g=Decimal("10"))
    assert not f.decrease_amount(Decimal("11"))
    assert f.weight_available_g == Decimal("10")
    assert f.decrease_amount(Decimal("10"))
    assert f.weight_available_g == Decimal("0")


def test_br3_product_whole_units():
    p = product(stock_quantity=3)
    assert not p.decrease_stock(4)
    assert p.stock_quantity == 3
    assert p.decrease_stock(3)
    assert p.stock_quantity == 0
    assert not p.increase_stock(0)


def test_br5_snapshot_uses_stored_amount():
    o = Order(quantity=3, filament_required_g=Decimal("60"), product_id=1, filament_id=1)
    assert o.calc_filament_used() == Decimal("60")


def test_display_names():
    f = filament(type="PLA", color="White", modifier="Matte")
    assert f.label == "Matte White"
    assert f.table_name == "PLA, Matte White"
    assert f.banner_name == "Matte White PLA"
    plain = filament(type="PETG", color="Black")
    assert plain.label == "Black"


def test_br14_password_hashing_roundtrip():
    from src.controllers import auth_controller
    h = auth_controller.hash_password("a-sufficiently-long-password")
    assert auth_controller.verify_password("a-sufficiently-long-password", h)
    assert not auth_controller.verify_password("wrong", h)
