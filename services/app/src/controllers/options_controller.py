"""SearchOptions: combobox option lookups."""
from sqlalchemy import select

from src.config import settings
from src.controllers import alert_controller
from src.formatting import fmt_amount
from src.models import Filament, Product


def _rank(rows, q: str, label_of):
    """Case-insensitive substring filter; prefix matches first, others alphabetical."""
    q = q.strip().lower()
    matched = [r for r in rows if q in label_of(r).lower()]
    prefix = [r for r in matched if label_of(r).lower().startswith(q)]
    rest = [r for r in matched if not label_of(r).lower().startswith(q)]
    prefix.sort(key=lambda r: label_of(r).lower())
    rest.sort(key=lambda r: label_of(r).lower())
    return prefix + rest


def _item(value, label, detail="", state="normal", amount="", **extra):
    item = {"value": value, "label": label, "detail": detail, "state": state, "amount": amount}
    item.update(extra)
    return item


def _payload(items, truncated):
    return {"items": items, "truncated": truncated, "page_size": settings.option_page_size}


def _state(item) -> str:
    amount = item.get_stock()
    if amount == 0:
        return "empty"
    if item.is_low_stock():
        return "low"
    return "normal"


def products(session, q: str):
    products_ = session.execute(select(Product)).scalars().all()
    filaments = session.execute(select(Filament)).scalars().all()
    ranked = _rank(products_, q, lambda p: p.name)
    out = []
    for p in ranked[: settings.option_page_size]:
        f = p.default_filament
 # Selecting a product pre-fills type and color from its default filament.
 # The order form's color field is a filament, so the id can only be pre-filled
        # When the type+color combination is unambiguous; otherwise just the label.
        prefill = [{"name": "type", "value": f.type, "label": f.type}]
        same = [x for x in filaments if x.type.lower() == f.type.lower() and x.color.lower() == f.color.lower()]
        if len(same) == 1:
            prefill.append({"name": "filament_id", "value": f.id, "label": f.table_name})
        else:
            prefill.append({"name": "filament_id", "value": "", "label": f.color})
        out.append(_item(
            p.id, p.name, state=_state(p),
            amount=fmt_amount("product", p.stock_quantity), prefill=prefill,
        ))
    return _payload(out, len(ranked) > settings.option_page_size)


def filament_types(session, q: str, for_: str):
    rows = session.execute(select(Filament)).scalars().all()
    types = sorted({f.type for f in rows}, key=str.lower)
    ranked = _rank([{"type": t} for t in types], q, lambda r: r["type"])
    out = []
    for r in ranked[: settings.option_page_size]:
        detail = ""
        if for_ == "add":
            n = sum(1 for f in rows if f.type.lower() == r["type"].lower())
            detail = f"{n} variants"
        out.append(_item(r["type"], r["type"], detail))
    truncated = len(ranked) > settings.option_page_size
    if for_ == "add" and q.strip():
        exact = any(t.lower() == q.strip().lower() for t in types)
        if not exact:
            out.append(_item(q.strip(), f'+ Create new "{q.strip()}"', "", "normal", create=True))
    return _payload(out, truncated)


def filaments(session, q: str, type_: str | None, style: str):
    rows = session.execute(select(Filament)).scalars().all()
    if type_:
        rows = [f for f in rows if f.type.lower() == type_.lower()]
    label_of = (lambda f: f.table_name) if style == "table" else (lambda f: f.label)
    ranked = _rank(rows, q, label_of)
    page = ranked[: settings.option_page_size]
    # Labels that collide across brands → append brand to secondary detail
    counts = {}
    for f in page:
        counts[label_of(f).lower()] = counts.get(label_of(f).lower(), 0) + 1
    out = []
    for f in page:
        detail = f.brand if counts[label_of(f).lower()] > 1 and f.brand else ""
        out.append(_item(f.id, label_of(f), detail, _state(f), amount=fmt_amount("filament", f.get_stock())))
    return _payload(out, len(ranked) > settings.option_page_size)


def colors(session, q: str, type_: str):
    rows = session.execute(select(Filament)).scalars().all()
    colors_ = sorted({f.color for f in rows if f.type.lower() == (type_ or "").lower()}, key=str.lower)
    ranked = _rank([{"color": c} for c in colors_], q, lambda r: r["color"])
    out = [_item(r["color"], r["color"]) for r in ranked[: settings.option_page_size]]
    return _payload(out, len(ranked) > settings.option_page_size)


def modifiers(session, q: str, type_: str, color: str):
    rows = session.execute(select(Filament)).scalars().all()
    matching = [f for f in rows if f.type.lower() == (type_ or "").lower() and f.color.lower() == (color or "").lower()]
    mods = sorted({f.modifier for f in matching if f.modifier}, key=str.lower)
    ranked = _rank([{"modifier": m} for m in mods], q, lambda r: r["modifier"])
    out = [_item(m, m) for m in ranked[: settings.option_page_size]]
    if any(f.modifier == "" for f in matching):
        out.insert(0, _item("", "None"))
    return _payload(out, len(ranked) > settings.option_page_size)
