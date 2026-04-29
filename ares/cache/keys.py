from __future__ import annotations

import hashlib
import json
from typing import Any

from ares.config import settings


def cache_key(namespace: str, *parts: Any) -> str:
    """Build a stable namespaced cache key."""
    serialized = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"{settings.CACHE_KEY_PREFIX}:{namespace}:{digest}"
