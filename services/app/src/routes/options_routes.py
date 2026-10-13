"""SearchOptions routes: JSON option lookups for comboboxes."""
from flask import Blueprint, g, jsonify, request

from src.controllers import options_controller

bp = Blueprint("options", __name__)


@bp.route("/options/products")
def products():
    return jsonify(options_controller.products(g.db_session, request.args.get("q", "")))


@bp.route("/options/filament-types")
def filament_types():
    return jsonify(options_controller.filament_types(
        g.db_session, request.args.get("q", ""), request.args.get("for", "")))


@bp.route("/options/filaments")
def filaments():
    return jsonify(options_controller.filaments(
        g.db_session, request.args.get("q", ""), request.args.get("type"),
        request.args.get("style", "label")))


@bp.route("/options/colors")
def colors():
    return jsonify(options_controller.colors(g.db_session, request.args.get("q", ""), request.args.get("type", "")))


@bp.route("/options/modifiers")
def modifiers():
    return jsonify(options_controller.modifiers(
        g.db_session, request.args.get("q", ""), request.args.get("type", ""),
        request.args.get("color", "")))
