from __future__ import annotations

from typing import Any


def promotion_form_key(run_id: str) -> str:
    return f"show_promote_form_{run_id}"


def rollback_form_key(entry_id: str) -> str:
    return f"show_rollback_{entry_id}"


def rollback_payload(target_run_id: str, actor: str, reason: str | None, *, dry_run: bool = False) -> dict[str, Any]:
    return {
        "target_run_id": target_run_id,
        "rolled_back_by": actor.strip(),
        "reason": (reason or "Dashboard rollback").strip() or "Dashboard rollback",
        "dry_run": dry_run,
    }


def risk_label(delta: float) -> str:
    abs_delta = abs(delta)
    if abs_delta > 0.05:
        return "High"
    if abs_delta > 0.02:
        return "Medium"
    return "Low"
