"""Scheduler process entry point."""
import logging

from src.services import alert_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

if __name__ == "__main__":
    alert_scheduler.run_forever()
