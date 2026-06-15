#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

STATUS_EMOJIS = {
    "improved": "✅ *Improved*",
    "within_tolerance": "✓ *Within Tolerance*",
    "regressed": "❌ **Regressed**",
    "baseline": "✓ *Baseline*",
    "missing": "⚠️ *Missing*",
}


def build_markdown_comment(payload: dict[str, any]) -> str:
    passed = payload.get("passed", False)
    run_id = payload.get("run_id", "Unknown")
    details_url = payload.get("details_url", "")
    failure_reason = payload.get("failure_reason", "")
    narrative = payload.get("decision_narrative", "")

    status_str = "🟢 **PASS**" if passed else "🔴 **FAIL**"
    details_link = f" ([View Dashboard]({details_url}))" if details_url else ""

    markdown = []
    markdown.append(f"## ⚔️ ARES Model Regression Gate: {status_str}{details_link}")
    
    if narrative:
        markdown.append(f"\n> **Decision Narrative:** {narrative}")
    
    if failure_reason:
        markdown.append(f"\n> ⚠️ **Failure Reason:** {failure_reason}")

    # Metric Table
    metric_table = payload.get("metric_table", {})
    if metric_table:
        markdown.append("\n### 📊 Performance Metrics")
        markdown.append("| Metric | Champion | Candidate | Delta | Status |")
        markdown.append("| :--- | :---: | :---: | :---: | :--- |")
        for metric, info in sorted(metric_table.items()):
            champ = f"{info['champion']:.4f}" if isinstance(info["champion"], (int, float)) else str(info["champion"])
            cand = f"{info['candidate']:.4f}" if isinstance(info["candidate"], (int, float)) else str(info["candidate"])
            delta = info["delta"]
            delta_str = f"{delta:+.4f}" if isinstance(delta, (int, float)) else str(delta)
            status_emoji = STATUS_EMOJIS.get(info["status"], str(info["status"]))
            markdown.append(f"| `{metric}` | {champ} | {cand} | {delta_str} | {status_emoji} |")

    # Slice Comparison
    slice_comparison = payload.get("slice_comparison", [])
    if slice_comparison:
        markdown.append("\n### 🧩 Slice Verification")
        markdown.append("| Slice | Critical | Champion F1 | Candidate F1 | Delta | Status |")
        markdown.append("| :--- | :---: | :---: | :---: | :---: | :--- |")
        for row in slice_comparison:
            is_critical = "⚠️ **Yes**" if row.get("is_critical") else "No"
            champ_f1 = f"{row['champion_f1']:.4f}" if isinstance(row.get("champion_f1"), (int, float)) else "-"
            cand_f1 = f"{row['candidate_f1']:.4f}" if isinstance(row.get("candidate_f1"), (int, float)) else "-"
            delta = row.get("delta")
            delta_str = f"{delta:+.4f}" if isinstance(delta, (int, float)) else "-"
            status_emoji = STATUS_EMOJIS.get(row["status"], str(row["status"]))
            markdown.append(f"| `{row['slice']}` | {is_critical} | {champ_f1} | {cand_f1} | {delta_str} | {status_emoji} |")

    markdown.append(f"\n*Run ID: `{run_id}` • Evaluation pipeline executed automatically.*")
    return "\n".join(markdown)


def post_to_github(
    comment_body: str,
    repository: str,
    pr_number: int,
    token: str,
) -> bool:
    url = f"https://api.github.com/repos/{repository}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    
    print(f"Posting evaluation comment to GitHub PR #{pr_number} in repo '{repository}'...")
    try:
        response = httpx.post(url, json={"body": comment_body}, headers=headers, timeout=10.0)
        response.raise_for_status()
        print("GitHub PR comment posted successfully.")
        return True
    except Exception as e:
        print(f"Failed to post GitHub comment: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Post Ares evaluation result as a GitHub PR comment")
    parser.add_argument("--result-json", default="reports/ares_result.json", help="Path to Ares evaluation result JSON")
    parser.add_argument("--github-repository", help="GitHub owner/repository (e.g. Rytnix786/Ares)")
    parser.add_argument("--pr-number", type=int, help="Pull Request number")
    parser.add_argument("--github-token", help="GitHub Personal Access Token or GITHUB_TOKEN")
    args = parser.parse_args()

    # Read result json
    path = Path(args.result_json)
    if not path.exists():
        print(f"Error: Result file not found at '{path}'")
        sys.exit(1)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading result JSON: {e}")
        sys.exit(1)

    # Format comment
    comment_body = build_markdown_comment(payload)
    print("\n--- Formatted PR Comment ---")
    print(comment_body)
    print("----------------------------\n")

    # Post to github if args provided or environments configured
    repo = args.github_repository or os.getenv("GITHUB_REPOSITORY")
    pr = args.pr_number or int(os.getenv("GITHUB_PR_NUMBER") or os.getenv("PR_NUMBER") or 0)
    token = args.github_token or os.getenv("GITHUB_TOKEN")

    if repo and pr and token:
        post_to_github(comment_body, repo, pr, token)
    else:
        print("Skipping GitHub API post: missing repo, PR number, or token configuration.")


if __name__ == "__main__":
    main()
