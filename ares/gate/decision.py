from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GateDecision:
    verdict: str
    passed: bool
    reason: str
    deltas: dict[str, float] = field(default_factory=dict)
    slice_regressions: list[dict[str, float | str]] = field(default_factory=list)
    should_promote: bool = False