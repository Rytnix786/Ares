from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a k6 summary against ARES Phase 3 budgets.")
    parser.add_argument("summary", type=Path)
    parser.add_argument("--max-p95-ms", type=float, default=750.0)
    parser.add_argument("--max-failure-rate", type=float, default=0.01)
    args = parser.parse_args()

    data = json.loads(args.summary.read_text(encoding="utf-8"))
    p95 = float(data["metrics"]["http_req_duration"]["percentiles"]["95"])
    failure_rate = float(data["metrics"]["http_req_failed"]["rate"])
    if p95 > args.max_p95_ms:
        raise SystemExit(f"p95 latency {p95}ms exceeds budget {args.max_p95_ms}ms")
    if failure_rate > args.max_failure_rate:
        raise SystemExit(f"failure rate {failure_rate} exceeds budget {args.max_failure_rate}")
    print(f"ARES load budget passed: p95={p95}ms failure_rate={failure_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
