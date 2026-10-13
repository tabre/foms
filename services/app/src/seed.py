"""Seed script: loads services/app/src/data/filament.csv.
Run with: uv run python -m src.seed
"""
import csv
from decimal import Decimal
from pathlib import Path

from src.controllers import alert_controller
from src.db import SessionLocal
from src.models import Filament

CSV_PATH = Path(__file__).parent / "data" / "filament.csv"


def normalize_threshold(raw: str) -> Decimal:
    """CSV 'None' and 'Special' thresholds become 0 (never triggers, )."""
    raw = (raw or "").strip()
    if raw in ("", "None", "Special"):
        return Decimal("0")
    return Decimal(raw)


def seed() -> int:
    created = 0
    with SessionLocal() as session:
        with open(CSV_PATH, newline="") as fh:
            for row in csv.DictReader(fh):
                combo = {
                    "brand": (row.get("brand") or "").strip(),
                    "type": (row.get("material") or "").strip(),
                    "modifier": (row.get("variant") or "").strip(),
                    "color": (row.get("color") or "").strip(),
                }
                existing = session.query(Filament).filter(
                    Filament.brand.ilike(combo["brand"]),
                    Filament.type.ilike(combo["type"]),
                    Filament.modifier.ilike(combo["modifier"]),
                    Filament.color.ilike(combo["color"]),
                ).first()
                if existing is not None:
                    continue
                f = Filament(
                    brand=combo["brand"], type=combo["type"],
                    modifier=combo["modifier"], color=combo["color"],
                    weight_available_g=Decimal(row.get("quantity") or "0"),
                    low_stock_threshold_g=normalize_threshold(row.get("reorder")),
                )
                session.add(f)
                session.commit()
                alert_controller.evaluate(session, "filament", f)
                created += 1
    return created


if __name__ == "__main__":
    print(f"Seeded {seed()} filaments.")
