from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import session_scope
from app.services.preheat_service import PreheatService


logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging()
    logger.info("preheat worker started")

    while True:
        try:
            if settings.preheat_enabled:
                with session_scope() as db:
                    result = PreheatService(db).preheat(
                        limit=settings.preheat_limit,
                        min_hot_score=settings.preheat_min_hot_score,
                    )
                    logger.info(
                        "preheat cycle finished candidates=%s refreshed=%s fallback=%s failed=%s",
                        result.scanned_candidates,
                        result.refreshed_count,
                        result.fallback_count,
                        result.failed_count,
                    )
            time.sleep(settings.preheat_poll_interval_seconds)
        except Exception:
            logger.exception("preheat worker loop failed")
            time.sleep(settings.preheat_poll_interval_seconds)


if __name__ == "__main__":
    main()
