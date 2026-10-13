"""Order routes: new order, warning fragment, orders list, complete, delete."""
from flask import Blueprint, flash, g, redirect, render_template, request

from src import errors as E
from src.controllers import order_controller
from src.models import Filament, Product
from src.routes import error_dict # Noqa: F401 (used by create path)

bp = Blueprint("order", __name__)


@bp.route("/orders/new")
def new_order():
    return render_template("new_order.html", form={}, errors={})


@bp.route("/orders/new/warning")
def order_warning():
    product = g.db_session.get(Product, int(request.args.get("product_id") or 0))
    filament = g.db_session.get(Filament, int(request.args.get("filament_id") or 0))
    try:
        quantity = int(request.args.get("quantity") or 0)
    except ValueError:
        quantity = 0
    warning = None
    if product and filament and quantity > 0:
        required = quantity * product.weight_per_unit_g
        if required > filament.weight_available_g:
            warning = E.order_needs_more_filament(required, filament.weight_available_g, filament.table_name)
    return render_template("fragments/order_warning.html", warning=warning)


def _orders_context(error=None):
    ctx = order_controller.list_orders(
        g.db_session,
        open_page=int(request.args.get("open_page") or 1),
        done_page=int(request.args.get("done_page") or 1),
    )
    ctx["error"] = error
    return ctx


@bp.route("/orders", methods=["GET", "POST"])
def orders():
    if request.method == "POST":
        cleaned, errs = order_controller.validate_create(request.form)
        if errs:
            return render_template("new_order.html", form=cleaned, errors=error_dict(errs))
        number, err = order_controller.create(g.db_session, cleaned)
        if err:
            return render_template("new_order.html", form=cleaned, errors={"Product": E.message(err)})
        flash(f"Order #{number} created.", "success")
        return redirect("/orders/new")
    return render_template("orders.html", **_orders_context())


@bp.route("/orders/<int:order_id>/complete", methods=["POST"])
def complete_order(order_id: int):
    order, err = order_controller.complete(g.db_session, order_id)
    if err:
        return render_template("fragments/orders_region.html", **_orders_context(E.message(err)))
    return render_template("fragments/orders_region.html", **_orders_context())


@bp.route("/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id: int):
    ok, err = order_controller.delete(g.db_session, order_id)
    if err:
        return render_template("fragments/orders_region.html", **_orders_context(E.message(err)))
    return render_template("fragments/orders_region.html", **_orders_context())
