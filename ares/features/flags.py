from __future__ import annotations

from collections.abc import Mapping

from ares.config import settings


class FeatureFlags:
    def __init__(self, flags: Mapping[str, bool] | None = None) -> None:
        self.flags = dict(settings.ARES_FEATURE_FLAGS if flags is None else flags)

    def is_enabled(self, name: str, default: bool = False) -> bool:
        return bool(self.flags.get(name, default))


def is_enabled(name: str, default: bool = False) -> bool:
    return FeatureFlags().is_enabled(name, default)
