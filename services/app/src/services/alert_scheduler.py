"""Services layer: alertScheduler. Runs for the whole system at a
fixed interval, independent of user requests."""
import logging
import time

from src.controllers import alert_controller
from src.db import SessionLocal

log = logging.getLogger("foms.scheduler")


def run_once() -> None:
    from src.config import settings
    session = SessionLocal()
    try:
        alert_controller.evaluate(session)
    finally:
        session.close()


def run_forever() -> None:
    from src.config import settings
    while True:
        try:
            run_once()
        except Exception as exc: # MUST log failures and continue
            log.error("alert evaluation failed: %s", exc)
        time.sleep(settings.alert_interval_seconds)
