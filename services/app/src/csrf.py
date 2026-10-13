"""CSRF protection. Double-submit cookie: the token is read from an
HttpOnly cookie on GET and echoed in every state-changing form."""
import secrets

from flask import g
from itsdangerous import URLSafeTimedSerializer

from src.config import settings

_serializer = URLSafeTimedSerializer(settings.secret)
COOKIE = "foms_csrf"


def signed(token: str) -> str:
    return _serializer.dumps(token)


def get_or_new() -> str:
    """Return the current CSRF token, generating one if the cookie is absent/invalid."""
    cookie = request_cookie()
    try:
        token = _serializer.loads(cookie, max_age=86400 * 30)
    except Exception:
        token = secrets.token_hex(16)
    g.csrf_token = token
    return token


def request_cookie() -> str:
    from flask import request
    return request.cookies.get(COOKIE) or ""


def valid() -> bool:
    from flask import request
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
    try:
        stored = _serializer.loads(request_cookie(), max_age=86400 * 30)
    except Exception:
        return False
    return bool(submitted) and secrets.compare_digest(submitted, stored)
