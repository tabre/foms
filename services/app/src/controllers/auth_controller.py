"""Authentication and user management."""
import logging
import secrets
from datetime import timedelta, timezone

import bcrypt
from sqlalchemy import select

from src.config import settings
from src.models import LoginThrottle, Session, User, utcnow

log = logging.getLogger("foms.auth")


def hash_password(password: str) -> str:
    # Salted, deliberately slow, adaptive one-way hash
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, credential: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), credential.encode("utf-8"))
    except ValueError:
        return False


def find_user(session, username: str) -> User | None:
    return session.execute(
        select(User).where(User.username.ilike(username.strip()))
    ).scalar_one_or_none()


def _throttle_row(session, username: str) -> LoginThrottle:
    key = username.strip().lower()
    row = session.get(LoginThrottle, key)
    if row is None:
        row = LoginThrottle(username=key)
        session.add(row)
    return row


def sign_in(session, username: str, password: str):
    """Returns (user, error). Applies throttling."""
    row = _throttle_row(session, username)
    now = utcnow()
    if row.locked_until and row.locked_until > now:
        log.info("auth: throttled sign-in attempt for %s", username.strip().lower())
        return None, E.TOO_MANY_ATTEMPTS

    user = find_user(session, username)
    if user is None or not user.active or not verify_password(password, user.credential):
        row.consecutive_failures += 1
        if row.consecutive_failures >= settings.failed_login_limit:
            row.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            log.info("auth: lockout for %s until %s", row.username, row.locked_until)
        session.commit()
        log.info("auth: failed sign-in for %s", username.strip().lower())
        return None, E.INVALID_CREDENTIALS

    row.consecutive_failures = 0
    row.locked_until = None
    user.last_login_at = now
    session.commit()
    log.info("auth: sign-in success for %s", user.username)
    return user, None


def create_session(session, user: User, remember: bool) -> Session:
    now = utcnow()
    duration = timedelta(days=settings.remember_days) if remember else timedelta(hours=settings.session_hours)
    row = Session(
        id=secrets.token_urlsafe(32), # Unpredictable
        user_id=user.id,
        created_at=now,
        last_activity_at=now,
        expires_at=now + duration,
        remember=remember,
    )
    session.add(row)
    session.commit()
    return row


def load_session(session, session_id: str) -> Session | None:
    if not session_id:
        return None
    row = session.get(Session, session_id)
    if row is None:
        return None
    now = utcnow()
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires <= now:
        session.delete(row)
        session.commit()
        return None
    duration = timedelta(days=settings.remember_days) if row.remember else timedelta(hours=settings.session_hours)
    row.last_activity_at = now
    row.expires_at = now + duration # Inactivity expiry
    session.commit()
    return row


def end_session(session, session_id: str) -> None:
    row = session.get(Session, session_id)
    if row is not None:
        session.delete(row)
        session.commit()
