import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_stats_cards import (  # noqa: E402
    THEME,
    aggregate_languages,
    compute_streaks,
    render_langs_svg,
    render_stats_svg,
)


def _days(counts):
    return [
        {"date": f"2026-07-{i + 1:02d}", "contributionCount": c}
        for i, c in enumerate(counts)
    ]


def test_compute_streaks_basic():
    current, longest = compute_streaks(_days([1, 1, 0, 1, 1, 1]))
    assert current == 3
    assert longest == 3


def test_compute_streaks_today_zero_keeps_current():
    current, longest = compute_streaks(_days([1, 1, 1, 0]))
    assert current == 3
    assert longest == 3


def test_compute_streaks_all_zero():
    current, longest = compute_streaks(_days([0, 0, 0]))
    assert current == 0
    assert longest == 0


def test_aggregate_languages_ranks_and_percentages():
    repos = [
        {
            "languages": {
                "edges": [
                    {"size": 750, "node": {"name": "Python", "color": "#3572A5"}},
                    {"size": 150, "node": {"name": "Rust", "color": "#dea584"}},
                ]
            }
        },
        {
            "languages": {
                "edges": [
                    {"size": 100, "node": {"name": "Shell", "color": None}},
                ]
            }
        },
    ]
    langs = aggregate_languages(repos, top=2)
    assert [name for name, _, _ in langs] == ["Python", "Rust"]
    assert abs(langs[0][2] - 75.0) < 0.01
    assert abs(langs[1][2] - 15.0) < 0.01


def test_aggregate_languages_null_color_falls_back():
    repos = [
        {
            "languages": {
                "edges": [{"size": 10, "node": {"name": "Shell", "color": None}}]
            }
        }
    ]
    langs = aggregate_languages(repos)
    assert langs[0][1] == THEME["muted"]


def test_render_stats_svg_contains_metrics():
    svg = render_stats_svg(
        {
            "commits": 578,
            "pull_requests": 147,
            "issues": 184,
            "total_contributions": 5103,
            "current_streak": 12,
            "longest_streak": 34,
        }
    )
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    for needle in ["578", "147", "184", "5103", "12 days", "34 days", THEME["bg"]]:
        assert needle in svg


def test_render_langs_svg_contains_languages():
    svg = render_langs_svg(
        [("Python", "#3572A5", 75.0), ("Rust", "#dea584", 25.0)]
    )
    assert svg.startswith("<svg")
    assert "Python 75.0%" in svg
    assert "Rust 25.0%" in svg
    assert "#3572A5" in svg
