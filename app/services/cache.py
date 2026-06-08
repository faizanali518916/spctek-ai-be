import time
from dataclasses import dataclass
from typing import Any

from app.config import get_settings


_MISSING = object()


@dataclass
class CachedResponse:
    body: bytes
    status_code: int
    media_type: str | None
    headers: dict[str, str]


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        settings = get_settings()
        if not settings.CACHE_ENABLED:
            return _MISSING

        item = self._store.get(key)
        if item is None:
            return _MISSING

        expires_at, value = item
        if expires_at <= time.monotonic():
            self._store.pop(key, None)
            return _MISSING

        return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> Any:
        settings = get_settings()
        if not settings.CACHE_ENABLED:
            return value

        ttl = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_SECONDS
        self._store[key] = (time.monotonic() + ttl, value)
        return value

    def clear(self) -> None:
        self._store.clear()


cache = TTLCache()


def cache_key(method: str, url: str) -> str:
    return f"response:{method.upper()}:{url}"


def cache_get(key: str) -> tuple[bool, Any]:
    value = cache.get(key)
    return value is not _MISSING, value
