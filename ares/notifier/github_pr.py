from __future__ import annotations


def build_pr_comment(result: dict) -> str:
    icon = "✅" if result.get("passed") else "❌"
    title = "Ares Gate: PASSED" if result.get("passed") else "Ares Gate: REGRESSION DETECTED"
    lines = [f"## {icon} {title}", ""]
    if result.get("details_url"):
        lines.append(f"Details: {result['details_url']}")
    return "\n".join(lines)