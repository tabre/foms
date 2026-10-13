"""Option ranking: prefix matches first, then alphabetical."""
from types import SimpleNamespace

from src.controllers.options_controller import _rank


def labels(rows):
    return [r.label for r in rows]


def test_prefix_first_then_alphabetical():
    rows = [
        SimpleNamespace(label="Blue"),
        SimpleNamespace(label="Sky Blue"),
        SimpleNamespace(label="Bluish"),
        SimpleNamespace(label="Aqua"),
    ]
    ranked = _rank(rows, "bl", lambda r: r.label)
    assert labels(ranked) == ["Blue", "Bluish", "Sky Blue"]


def test_case_insensitive_matching():
    rows = [SimpleNamespace(label="White"), SimpleNamespace(label="white-ish")]
    ranked = _rank(rows, "WHITE", lambda r: r.label)
    assert labels(ranked) == ["White", "white-ish"]


from decimal import Decimal

from src.config import settings
from src.controllers import options_controller
from src.models import Filament, Product


def prefill_of(item):
    return {e["name"]: e for e in item["prefill"]}


def test_payload_reports_page_size(session):
    assert options_controller.colors(session, "", "PLA")["page_size"] == settings.option_page_size


def test_product_row_exposes_amount_and_state(session):
    f = Filament(type="PLA", color="White", weight_available_g=Decimal("100"))
    p = Product(name="Cone", default_filament=f, weight_per_unit_g=Decimal("20"),
               stock_quantity=2, low_stock_threshold=3)
    session.add_all([f, p])
    session.commit()
    item = options_controller.products(session, "cone")["items"][0]
    assert item["amount"] == "2 units"
    assert item["state"] == "low"
    assert item["detail"] == ""


def test_product_prefill_resolves_unique_filament(session):
    f = Filament(type="PLA", color="White", weight_available_g=Decimal("100"))
    p = Product(name="Cone", default_filament=f, weight_per_unit_g=Decimal("20"))
    session.add_all([f, p])
    session.commit()
    prefill = prefill_of(options_controller.products(session, "cone")["items"][0])
    assert prefill["type"]["value"] == "PLA"
    assert prefill["filament_id"]["value"] == f.id
    assert prefill["filament_id"]["label"] == f.table_name


def test_product_prefill_keeps_ambiguous_color_as_text(session):
    f1 = Filament(brand="Brand A", type="PETG", color="Black", weight_available_g=Decimal("100"))
    f2 = Filament(brand="Brand B", type="PETG", color="Black", weight_available_g=Decimal("100"))
    p = Product(name="Box", default_filament=f1, weight_per_unit_g=Decimal("20"))
    session.add_all([f1, f2, p])
    session.commit()
    prefill = prefill_of(options_controller.products(session, "box")["items"][0])
    assert prefill["type"]["value"] == "PETG"
    assert prefill["filament_id"]["value"] == ""
    assert prefill["filament_id"]["label"] == "Black"
