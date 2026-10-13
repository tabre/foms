"""Auth routes."""
from datetime import timedelta

from flask import Blueprint, g, make_response, redirect, render_template, request
from sqlalchemy import select

from src import errors as E
from src import validation as V
from src.config import settings
from src.controllers import auth_controller
from src.db import SessionLocal
from src.models import User
from src.routes import error_dict

bp = Blueprint("auth", __name__)


def _cookie(resp, session_row) -> None:
    duration = timedelta(days=settings.remember_days) if session_row.remember else timedelta(hours=settings.session_hours)
    resp.set_cookie(
        settings.session_cookie, session_row.id,
        httponly=True, secure=settings.cookie_secure, samesite="Lax",
        max_age=int(duration.total_seconds()),
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    with SessionLocal() as s:
        if s.execute(select(User)).first() is None:
            return redirect("/setup")
        if request.method == "GET":
            return render_template("login.html", error=None)

        user, err = auth_controller.sign_in(
            s, request.form.get("username", ""), request.form.get("password", "")
        )
        if err:
            return render_template("login.html", error=E.message(err))
        session_row = auth_controller.create_session(s, user, bool(request.form.get("remember")))
        resp = make_response(redirect(request.args.get("next") or "/"))
        _cookie(resp, session_row)
        return resp


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    with SessionLocal() as s:
        if s.execute(select(User)).first() is not None:
            return redirect("/login")
        if request.method == "GET":
            return render_template("setup.html", errors={})

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        errors = V.validate_username(username) + V.validate_password(password)
        if password != confirm:
            errors.append({"field": "Confirm password", "message": E.passwords_do_not_match()})
        if errors:
            return render_template("setup.html", errors=error_dict(errors))

        user = User(username=username, credential=auth_controller.hash_password(password))
        s.add(user)
        s.commit()
        session_row = auth_controller.create_session(s, user, False)
        resp = make_response(redirect("/"))
        _cookie(resp, session_row)
        return resp


@bp.route("/logout", methods=["POST"])
def logout():
    auth_controller.end_session(g.db_session, request.cookies.get(settings.session_cookie))
    resp = make_response(redirect("/login"))
    resp.delete_cookie(settings.session_cookie)
    return resp


@bp.route("/users")
def users():
    rows = g.db_session.execute(select(User)).scalars().all()
    return render_template("users.html", users=rows, error=None, pw_error=None)


@bp.route("/users", methods=["POST"])
def add_user():
    s = g.db_session
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    errors = V.validate_username(username) + V.validate_password(password)
    if not errors and auth_controller.find_user(s, username):
        errors.append({"field": "Username", "message": "That username already exists."})
    if errors:
        rows = s.execute(select(User)).scalars().all()
        return render_template("users.html", users=rows, error=error_dict(errors).get("Username"), pw_error=None)
    s.add(User(username=username, credential=auth_controller.hash_password(password)))
    s.commit()
    return redirect("/users")


@bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
def deactivate_user(user_id: int):
    s = g.db_session
    user = s.get(User, user_id)
    if user is None:
        return "Not found.", 404
    others = [u for u in s.execute(select(User).where(User.active.is_(True))).scalars() if u.id != user_id]
    if not others:
        rows = s.execute(select(User)).scalars().all()
        return render_template("users.html", users=rows, error=E.last_active_user_required(), pw_error=None)
    user.active = False
    s.commit()
    return redirect("/users")


@bp.route("/users/<int:user_id>/activate", methods=["POST"])
def activate_user(user_id: int):
    s = g.db_session
    user = s.get(User, user_id)
    if user is None:
        return "Not found.", 404
    user.active = True
    s.commit()
    return redirect("/users")


@bp.route("/users/change-password", methods=["POST"])
def change_password():
    s = g.db_session
    user = g.user
    current = request.form.get("current") or ""
    new = request.form.get("new") or ""
    confirm = request.form.get("confirm") or ""
    errors = []
    if not auth_controller.verify_password(current, user.credential):
        errors.append({"field": "Current password", "message": E.invalid_credentials()})
    errors += V.validate_password(new)
    if new != confirm:
        errors.append({"field": "Confirm new password", "message": E.passwords_do_not_match()})
    if errors:
        rows = s.execute(select(User)).scalars().all()
        d = error_dict(errors)
        return render_template("users.html", users=rows, error=None,
                              pw_error=d.get("Current password") or d.get("Password") or d.get("Confirm new password"))
    user.credential = auth_controller.hash_password(new)
    s.commit()
    return redirect("/users")
