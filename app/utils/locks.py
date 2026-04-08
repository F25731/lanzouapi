from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Optional

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

from app.core.config import get_settings


@dataclass
class LockHandle:
    key: str
    token: str
    lock: object
    client: object = None

    def release(self) -> None:
        if self.client is not None:
            current = self.client.get(self.key)
            if current and current.decode("utf-8") == self.token:
                self.client.delete(self.key)
            return
        self.lock.release()


class ResolveLockManager:
    def __init__(self) -> None:
        self._locks = {}
        self._guard = threading.Lock()
        self._redis_client = None

        settings = get_settings()
        if settings.redis_url and redis is not None:
            self._redis_client = redis.from_url(settings.redis_url)

    def acquire(self, key: str, ttl_seconds: int) -> Optional[LockHandle]:
        token = str(uuid.uuid4())
        if self._redis_client is not None:
            acquired = self._redis_client.set(key, token, nx=True, ex=ttl_seconds)
            if acquired:
                return LockHandle(
                    key=key,
                    token=token,
                    lock=None,
                    client=self._redis_client,
                )
            return None

        with self._guard:
            lock = self._locks.setdefault(key, threading.Lock())

        if lock.acquire(blocking=False):
            return LockHandle(key=key, token=token, lock=lock)
        return None

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


resolve_lock_manager = ResolveLockManager()
