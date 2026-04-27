from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    from slowapi import Limiter
except ModuleNotFoundError:  # pragma: no cover
    Limiter = None

from ares.api.auth import rate_limit_key


class _NoOpLimiter:
    def limit(self, _value: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator


limiter = Limiter(key_func=rate_limit_key) if Limiter is not None else _NoOpLimiter()