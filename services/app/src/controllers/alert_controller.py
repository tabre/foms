"""EvaluateAlerts and ListAlerts."""
import logging

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from src.models import Alert, Filament, Product, utcnow

log = logging.getLogger("foms.alerts")


def evaluate_item(session, kind: str, item) -> None:
    if item.is_low_stock():
        # Raise; the partial unique index makes concurrent runs safe
        stmt = (
            insert(Alert)
            .values(item_kind=kind, item_id=item.id, raised_at=utcnow())
            .on_conflict_do_nothing(
                index_elements=["item_kind", "item_id"],
                index_where=text("cleared_at IS NULL"),
            )
        )
        session.execute(stmt)
    else:
        active = session.execute(
            select(Alert).where(
                Alert.item_kind == kind,
                Alert.item_id == item.id,
                Alert.cleared_at.is_(None),
            )
        ).scalar_one_or_none()
        if active:
            active.cleared_at = utcnow() # Clear


def evaluate(session, kind: str | None = None, item=None) -> None:
    """Whole system or a single item."""
    if item is not None:
        evaluate_item(session, kind, item)
    else:
        for f in session.execute(select(Filament)).scalars():
            evaluate_item(session, "filament", f)
        for p in session.execute(select(Product)).scalars():
            evaluate_item(session, "product", p)
    session.commit()


def list_alerts(session):
    """Active alerts with live item data, newest first."""
    rows = session.execute(
        select(Alert).where(Alert.cleared_at.is_(None)).order_by(Alert.raised_at.desc())
    ).scalars().all()
    out = []
    for a in rows:
        item = session.get(Filament, a.item_id) if a.item_kind == "filament" else session.get(Product, a.item_id)
        if item is None: # Deleted items are deleted with their alerts
            continue
        out.append({"kind": a.item_kind, "item": item, "raised_at": a.raised_at})
    return out
