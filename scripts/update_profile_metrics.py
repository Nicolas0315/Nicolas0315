#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

OWNER = "Nicolas0315"
REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"

QUERY = {
    "query": """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """,
    "variables": {"login": OWNER},
}


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    raise SystemExit("GITHUB_TOKEN or GH_TOKEN is required")


def fetch_metrics(token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(QUERY).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Nicolas0315-profile-metrics",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    user = payload["data"]["user"]["contributionsCollection"]
    return {
        "commits": user["totalCommitContributions"],
        "pull_requests": user["totalPullRequestContributions"],
        "issues": user["totalIssueContributions"],
        "total_contributions": user["contributionCalendar"]["totalContributions"],
    }


def render_table(metrics: dict) -> str:
    return (
        "<!-- METRICS:START -->\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| Commits | {metrics['commits']} |\n"
        f"| Pull Requests | {metrics['pull_requests']} |\n"
        f"| Issues | {metrics['issues']} |\n"
        f"| Total Contributions | {metrics['total_contributions']} |\n\n"
        "<!-- METRICS:END -->"
    )


def main() -> int:
    token = get_token()
    metrics = fetch_metrics(token)
    readme = README.read_text(encoding="utf-8")
    updated = re.sub(
        r"<!-- METRICS:START -->.*?<!-- METRICS:END -->",
        render_table(metrics),
        readme,
        flags=re.S,
    )
    README.write_text(updated, encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
