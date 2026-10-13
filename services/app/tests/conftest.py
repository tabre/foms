import os

os.environ.setdefault("FOMS_SECRET", "test-secret")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db import engine
from src.models import Base


@pytest.fixture
def session():
    """In-memory session for pure entity-behavior tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def pg_session():
    """Postgres session for integration tests; skips gracefully when unreachable.
    Runs inside an outer transaction with the session attached as a savepoint,
    so commits made by a test never persist to the data store.
    """
    try:
        conn = engine.connect()
        conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL is not reachable")
    from sqlalchemy.orm import Session

    conn.rollback()  # release the transaction autobegun by the reachability check
    transaction = conn.begin()
    s = Session(bind=conn, join_transaction_mode="create_savepoint")
    Base.metadata.create_all(engine)
    yield s
    s.close()
    transaction.rollback()
    conn.close()
