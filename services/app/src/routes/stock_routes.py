"""Stock routes: dashboard, check stock, specific-filament lookup, row actions."""
from flask import Blueprint, flash, g, redirect, render_template, request

from src import errors as E
from src import validation as V
from src.controllers import alert_controller, filament_controller, product_controller
from src.routes import error_dict

bp = Blueprint("stock", __name__)


@bp.route("/")
def dashboard():
    return render_template("dashboard.html", alerts=alert_controller.list_alerts(g.db_session))


@bp.route("/stock")
def stock():
    filaments, products, alerts = filament_controller.check_stock(g.db_session)
    return render_template("stock.html", filaments=filaments, products=products, alerts=alerts)


@bp.route("/stock/filament")
def view_filament():
    return render_template("view_filament.html", result=None,
                           form_type=request.args.get("type", ""),
                           form_color=request.args.get("color", ""),
                           form_modifier=request.args.get("modifier", ""))


@bp.route("/stock/filament/result")
def view_filament_result():
    type_ = (request.args.get("type") or "").strip()
    color = (request.args.get("color") or "").strip()
    modifier = (request.args.get("modifier") or "").strip()
    if not type_ or not color:
        return render_template("view_filament.html", result=None,
                               form_type=type_, form_color=color, form_modifier=modifier)
    rows = filament_controller.find(g.db_session, type_, color, modifier)
    return render_template("view_filament.html", result=rows,
                           form_type=type_, form_color=color, form_modifier=modifier)


def _prefix(kind: str) -> str:
    return "f" if kind == "filament" else "p"


@bp.route("/stock/fragments/filament/<int:item_id>/adjust")
def adjust_form_filament(item_id: int):
    f = g.db_session.get(filament_controller.Filament, item_id)
    if f is None:
        return ""
    return render_template("fragments/adjust_form.html", kind="filament", prefix="f", id=item_id,
                           name=f.table_name, direction="increase", amount="", error=None)


@bp.route("/stock/fragments/product/<int:item_id>/adjust")
def adjust_form_product(item_id: int):
    p = g.db_session.get(product_controller.Product, item_id)
    if p is None:
        return ""
    return render_template("fragments/adjust_form.html", kind="product", prefix="p", id=item_id,
                           name=p.name, direction="increase", amount="", error=None)


@bp.route("/stock/fragments/filament/<int:item_id>/edit")
def edit_form_filament(item_id: int):
    f = g.db_session.get(filament_controller.Filament, item_id)
    return render_template("fragments/edit_filament_form.html", f=f, error=None) if f else ""


@bp.route("/stock/fragments/product/<int:item_id>/edit")
def edit_form_product(item_id: int):
    p = g.db_session.get(product_controller.Product, item_id)
    return render_template("fragments/edit_product_form.html", p=p, error=None) if p else ""


@bp.route("/filaments/<int:item_id>/adjust", methods=["POST"])
def adjust_filament(item_id: int):
    amount, errs = V.parse_adjust_amount(request.form.get("amount"), "Amount", grams=True)
    if errs:
        return _adjust_error("filament", "f", item_id, request.form.get("direction"), request.form.get("amount"), error_dict(errs))
    f, err = filament_controller.adjust(g.db_session, item_id, request.form.get("direction"), amount)
    if err:
        return _adjust_error("filament", "f", item_id, request.form.get("direction"), request.form.get("amount"), err)
    return render_template("fragments/filament_row.html", f=f)


@bp.route("/products/<int:item_id>/adjust", methods=["POST"])
def adjust_product(item_id: int):
    amount, errs = V.parse_adjust_amount(request.form.get("amount"), "Amount", grams=False)
    if errs:
        return _adjust_error("product", "p", item_id, request.form.get("direction"), request.form.get("amount"), error_dict(errs))
    p, err = product_controller.adjust(g.db_session, item_id, request.form.get("direction"), amount)
    if err:
        return _adjust_error("product", "p", item_id, request.form.get("direction"), request.form.get("amount"), err)
    return render_template("fragments/product_row.html", p=p)


def _adjust_error(kind, prefix, item_id, direction, amount, error):
    session = g.db_session
    name = session.get(filament_controller.Filament, item_id) if kind == "filament" else session.get(product_controller.Product, item_id)
    name = name.table_name if kind == "filament" else name.name
    return render_template("fragments/adjust_form.html", kind=kind, prefix=prefix, id=item_id,
                           name=name, direction=direction, amount=amount, error=E.message(error))


@bp.route("/filaments/<int:item_id>", methods=["POST"])
def edit_filament(item_id: int):
    cleaned, errs = filament_controller.validate_edit(request.form)
    if errs:
        f = g.db_session.get(filament_controller.Filament, item_id)
        d = error_dict(errs)
        return render_template("fragments/edit_filament_form.html", f=f,
                               error=d.get("Type") or d.get("Color") or next(iter(d.values()), None))
    f, err = filament_controller.edit(g.db_session, item_id, cleaned)
    if err:
        f = g.db_session.get(filament_controller.Filament, item_id)
        return render_template("fragments/edit_filament_form.html", f=f, error=E.message(err))
    return render_template("fragments/filament_row.html", f=f)


@bp.route("/products/<int:item_id>", methods=["POST"])
def edit_product(item_id: int):
    cleaned, errs = product_controller.validate_edit(request.form)
    if errs:
        p = g.db_session.get(product_controller.Product, item_id)
        d = error_dict(errs)
        return render_template("fragments/edit_product_form.html", p=p,
                               error=d.get("Name") or d.get("Weight per unit (g)") or next(iter(d.values()), None))
    p, err = product_controller.edit(g.db_session, item_id, cleaned)
    if err:
        p = g.db_session.get(product_controller.Product, item_id)
        return render_template("fragments/edit_product_form.html", p=p, error=E.message(err))
    return render_template("fragments/product_row.html", p=p)


@bp.route("/filaments/<int:item_id>", methods=["DELETE"])
def delete_filament(item_id: int):
    ok, err = filament_controller.delete(g.db_session, item_id)
    if err:
        return render_template("fragments/error_row.html", error=E.message(err))
    return ""


@bp.route("/products/<int:item_id>", methods=["DELETE"])
def delete_product(item_id: int):
    ok, err = product_controller.delete(g.db_session, item_id)
    if err:
        return render_template("fragments/error_row.html", error=E.message(err))
    return ""


@bp.route("/items/new")
def add_item():
    return render_template("add_item.html", kind=request.args.get("kind", "filament"), errors={})


@bp.route("/filaments", methods=["POST"])
def create_filament():
    cleaned, errs = filament_controller.validate_add(request.form)
    kind = "filament"
    if errs:
        return render_template("add_item.html", kind=kind, errors=error_dict(errs))
    _id, err = filament_controller.add(g.db_session, cleaned)
    if err:
        return render_template("add_item.html", kind=kind, errors={"Type": err})
    flash("Filament added.", "success")
    return redirect(f"/items/new?kind={kind}")


@bp.route("/products", methods=["POST"])
def create_product():
    cleaned, errs = product_controller.validate_add(request.form)
    kind = "product"
    if errs:
        return render_template("add_item.html", kind=kind, errors=error_dict(errs))
    _id, err = product_controller.add(g.db_session, cleaned)
    if err:
        return render_template("add_item.html", kind=kind, errors={"Name": err})
    flash("Product added.", "success")
    return redirect(f"/items/new?kind={kind}")
