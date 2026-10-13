"""Main server: app factory, authentication gate, CSRF, security headers."""
import logging

from flask import Flask, g, redirect, request, url_for
from sqlalchemy import select

from src import csrf
from src.config import settings
from src.controllers import auth_controller
from src.db import SessionLocal
from src.models import User
from src.routes import register_blueprints

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("foms")

EXEMPT = {"/login", "/setup", "/health"}

app = Flask(__name__)
register_blueprints(app)

from src.formatting import fmt_amount, fmt_threshold, fmt_timestamp, fmt_date, utc_iso

app.jinja_env.filters["fmt_amount"] = lambda value, kind: fmt_amount(kind, value)
app.jinja_env.filters["fmt_threshold"] = lambda value, kind: fmt_threshold(kind, value)
app.jinja_env.filters["fmt_timestamp"] = fmt_timestamp
app.jinja_env.filters["fmt_date"] = fmt_date
app.jinja_env.filters["utc_iso"] = utc_iso


def _is_noninteractive() -> bool:
    return bool(request.headers.get("HX-Request")) or request.accept_mimetypes.best == "application/json"


@app.before_request
def authenticate():
    path = request.path
    if path.startswith("/static") or path in EXEMPT:
        if request.method == "GET":
            g.csrf_token = csrf.get_or_new()
        return
    if request.method == "GET":
        g.csrf_token = csrf.get_or_new()

    session = SessionLocal()
    g.db_session = session

    row = auth_controller.load_session(session, request.cookies.get(settings.session_cookie))
    if row is None:
        has_users = session.execute(select(User)).first()
        if has_users is None: # First-run: present and nothing else
            if _is_noninteractive():
                return "Setup required.", 401
            return redirect("/setup")
        if _is_noninteractive():
            return "Authentication required.", 401
        return redirect(f"/login?next={path}")

    g.session_row = row
    g.user = row.user

    if request.method in ("POST", "PATCH", "DELETE"):
        if not csrf.valid():
            log.info("auth: CSRF failure for user %s", g.user.username)
            return "Invalid or expired form token.", 400


@app.after_request
def finalize(response):
    # CSRF double-submit cookie
    if request.method == "GET" and getattr(g, "csrf_token", None):
        response.set_cookie(
            "foms_csrf", csrf.signed(g.csrf_token),
            httponly=True, secure=settings.cookie_secure, samesite="Lax", path="/",
        )
    # Security-relevant response headers
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;",
    )
    if settings.cookie_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


@app.teardown_request
def close_session(exc):
    session = getattr(g, "db_session", None)
    if session is not None:
        session.close()


@app.route("/health")
def health():
    """Unauthenticated liveness check."""
    try:
        from sqlalchemy import text
        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "data store unreachable", 503


app.secret_key = settings.secret


@app.context_processor
def injects():
    return {
        "user": getattr(g, "user", None),
        "csrf_token": lambda: getattr(g, "csrf_token", ""),
        "on_dashboard": request.path == "/",
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
