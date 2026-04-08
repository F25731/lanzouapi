from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import session_scope
from app.services.scan_service import ScanService


logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging()
    logger.info("scan worker started")

    while True:
        try:
            with session_scope() as db:
                handled = ScanService(db).run_next_pending_job()
            if not handled:
                time.sleep(settings.scan_poll_interval_seconds)
        except Exception:
            logger.exception("scan worker loop failed")
            time.sleep(settings.scan_poll_interval_seconds)


if __name__ == "__main__":
    main()
