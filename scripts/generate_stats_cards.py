#!/usr/bin/env python3
"""Generate self-hosted profile stat card SVGs (tokyonight theme).

Queries the GitHub GraphQL API with the Actions GITHUB_TOKEN (public data
only) and renders dist/stats-card.svg and dist/top-langs.svg. No third-party
card services involved, so the cards cannot break when shared instances
pause or hit rate limits.
"""
import json
import os
import urllib.request
from pathlib import Path

OWNER = "Nicolas0315"
OUT_DIR = Path(os.environ.get("OUT_DIR", "dist"))

THEME = {
    "bg": "#1a1b27",
    "title": "#70a5fd",
    "text": "#38bdae",
    "accent": "#bf91f3",
    "muted": "#565f89",
}

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
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
        repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
          nodes {
            languages(first: 10) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
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


def fetch_user(token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(QUERY).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Nicolas0315-profile-cards",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["data"]["user"]


def compute_streaks(days: list) -> tuple:
    """Return (current, longest) streaks in days.

    days: chronologically ordered [{"date": ..., "contributionCount": n}, ...]
    covering the past year. The trailing day (today) does not break the
    current streak while it is still at zero contributions.
    """
    longest = run = 0
    for day in days:
        run = run + 1 if day["contributionCount"] > 0 else 0
        longest = max(longest, run)

    current = 0
    tail = list(reversed(days))
    if tail and tail[0]["contributionCount"] == 0:
        tail = tail[1:]
    for day in tail:
        if day["contributionCount"] == 0:
            break
        current += 1
    return current, longest


def aggregate_languages(repo_nodes: list, top: int = 6) -> list:
    """Return [(name, color, pct), ...] for the top languages by bytes."""
    sizes = {}
    colors = {}
    for repo in repo_nodes:
        for edge in (repo.get("languages") or {}).get("edges") or []:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
            colors[name] = edge["node"].get("color") or THEME["muted"]
    total = sum(sizes.values()) or 1
    ranked = sorted(sizes.items(), key=lambda kv: -kv[1])[:top]
    return [(name, colors[name], 100.0 * size / total) for name, size in ranked]


def _svg_open(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none" role="img">\n'
        f'<style>text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Ubuntu,'
        f'sans-serif}}</style>\n'
        f'<rect width="{width}" height="{height}" rx="4.5" fill="{THEME["bg"]}"/>\n'
    )


def render_stats_svg(metrics: dict) -> str:
    rows = [
        ("Commits", metrics["commits"]),
        ("Pull Requests", metrics["pull_requests"]),
        ("Issues", metrics["issues"]),
        ("Contributions", metrics["total_contributions"]),
        ("Current Streak", f'{metrics["current_streak"]} days'),
        ("Longest Streak", f'{metrics["longest_streak"]} days'),
    ]
    width, height = 400, 215
    parts = [_svg_open(width, height)]
    parts.append(
        f'<text x="25" y="33" font-size="16" font-weight="600" '
        f'fill="{THEME["title"]}">GitHub Activity — past year</text>\n'
    )
    y = 63
    for label, value in rows:
        parts.append(
            f'<circle cx="30" cy="{y - 4}" r="3" fill="{THEME["accent"]}"/>\n'
            f'<text x="44" y="{y}" font-size="13" fill="{THEME["text"]}">{label}</text>\n'
            f'<text x="{width - 25}" y="{y}" font-size="13" font-weight="600" '
            f'text-anchor="end" fill="{THEME["title"]}">{value}</text>\n'
        )
        y += 26
    parts.append("</svg>\n")
    return "".join(parts)


def render_langs_svg(langs: list) -> str:
    width, height = 400, 215
    bar_x, bar_w = 25, width - 50
    parts = [_svg_open(width, height)]
    parts.append(
        f'<text x="25" y="33" font-size="16" font-weight="600" '
        f'fill="{THEME["title"]}">Top Languages — public repos</text>\n'
    )
    x = float(bar_x)
    parts.append(f'<rect x="{bar_x}" y="50" width="{bar_w}" height="10" rx="5" fill="{THEME["muted"]}"/>\n')
    for name, color, pct in langs:
        seg = bar_w * pct / 100.0
        parts.append(f'<rect x="{x:.1f}" y="50" width="{seg:.1f}" height="10" fill="{color}"/>\n')
        x += seg
    y = 92
    for i, (name, color, pct) in enumerate(langs):
        col_x = 25 if i % 2 == 0 else width // 2 + 5
        parts.append(
            f'<circle cx="{col_x + 5}" cy="{y - 4}" r="5" fill="{color}"/>\n'
            f'<text x="{col_x + 18}" y="{y}" font-size="13" fill="{THEME["text"]}">'
            f'{name} {pct:.1f}%</text>\n'
        )
        if i % 2 == 1:
            y += 26
    parts.append("</svg>\n")
    return "".join(parts)


def main() -> int:
    user = fetch_user(get_token())
    coll = user["contributionsCollection"]
    days = [
        day
        for week in coll["contributionCalendar"]["weeks"]
        for day in week["contributionDays"]
    ]
    current, longest = compute_streaks(days)
    metrics = {
        "commits": coll["totalCommitContributions"],
        "pull_requests": coll["totalPullRequestContributions"],
        "issues": coll["totalIssueContributions"],
        "total_contributions": coll["contributionCalendar"]["totalContributions"],
        "current_streak": current,
        "longest_streak": longest,
    }
    langs = aggregate_languages(user["repositories"]["nodes"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "stats-card.svg").write_text(render_stats_svg(metrics), encoding="utf-8")
    (OUT_DIR / "top-langs.svg").write_text(render_langs_svg(langs), encoding="utf-8")
    print(json.dumps({"metrics": metrics, "languages": [l[0] for l in langs]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
