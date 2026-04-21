#!/usr/bin/env python3
"""
Render journal/events.jsonl into human-readable markdown under docs/journal/.

Usage:
    python journal/render.py                 # render latest state
    python journal/render.py --limit 100     # override default event count

Outputs:
    docs/journal/index.md         -- latest N events, grouped by day
    docs/journal/by-subject.md    -- events grouped by subsystem
    docs/journal/archive.md       -- full chronology

Source of truth: journal/events.jsonl + journal/state.json.
The rendered files are build artifacts — never hand-edit them.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = REPO_ROOT / "journal" / "events.jsonl"
STATE_PATH = REPO_ROOT / "journal" / "state.json"
DOCS_DIR = REPO_ROOT / "docs" / "journal"

KIND_ICONS = {
    "done": "✓",
    "now": "•",
    "plan": "○",
    "decide": "◆",
    "blocked": "✗",
    "note": "·",
}


def load_events() -> list[dict]:
    events = []
    if not EVENTS_PATH.exists():
        return events
    with EVENTS_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    events.sort(key=lambda e: e.get("ts", ""))
    return events


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    with STATE_PATH.open() as f:
        return json.load(f)


def render_event_line(event: dict) -> str:
    ts = event.get("ts", "")
    kind = event.get("kind", "note")
    subject = event.get("subject", "")
    text = event.get("text", "")
    icon = KIND_ICONS.get(kind, "·")
    day = ts.split("T")[0] if "T" in ts else ts
    time = ts.split("T")[1].rstrip("Z")[:5] if "T" in ts else ""
    commit = event.get("commit", "")
    commit_suffix = f" `[{commit[:7]}]`" if commit else ""
    return f"- `{time}` {icon} **{subject}** — {text}{commit_suffix}"


def render_index(events: list[dict], state: dict, limit: int) -> str:
    recent = events[-limit:] if limit else events
    by_day: dict[str, list[dict]] = defaultdict(list)
    for e in recent:
        day = e.get("ts", "").split("T")[0]
        by_day[day].append(e)

    lines = [
        "# Fuzzi Journal",
        "",
        "What happened, what's happening, what's next. Source of truth is `journal/events.jsonl` — this page is rendered from it.",
        "",
        "## Right now",
        "",
    ]

    now = state.get("now", [])
    if now:
        for item in now:
            blocker = f" *(blocked: {item['blocker']})*" if item.get("blocker") else ""
            lane = f" `{item.get('lane', '')}`" if item.get("lane") else ""
            lines.append(f"- **{item['subject']}**{lane} — {item['text']}{blocker}")
    else:
        lines.append("_nothing in flight_")

    lines += ["", "## Up next", ""]
    nxt = state.get("next", [])
    if nxt:
        for item in nxt:
            lines.append(f"- {item}")
    else:
        lines.append("_queue empty_")

    lines += ["", "## Recent activity", ""]
    for day in sorted(by_day.keys(), reverse=True):
        lines.append(f"### {day}")
        lines.append("")
        for e in by_day[day]:
            lines.append(render_event_line(e))
        lines.append("")

    lines += [
        "## Legend",
        "",
        "- `✓ done` — delivered",
        "- `• now` — in flight",
        "- `○ plan` — queued",
        "- `◆ decide` — architectural decision",
        "- `✗ blocked` — waiting on something",
        "- `· note` — observation",
        "",
        f"_Rendered {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} from {len(events)} events._",
    ]
    return "\n".join(lines) + "\n"


def render_by_subject(events: list[dict]) -> str:
    by_subject: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        by_subject[e.get("subject", "unknown")].append(e)

    lines = [
        "# Journal by subject",
        "",
        "Every event grouped by the subsystem it touches.",
        "",
    ]
    for subject in sorted(by_subject.keys()):
        lines.append(f"## {subject}")
        lines.append("")
        for e in by_subject[subject]:
            day = e.get("ts", "").split("T")[0]
            icon = KIND_ICONS.get(e.get("kind", "note"), "·")
            commit = f" `[{e.get('commit', '')[:7]}]`" if e.get("commit") else ""
            lines.append(f"- `{day}` {icon} {e.get('text', '')}{commit}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_archive(events: list[dict]) -> str:
    lines = [
        "# Full chronology",
        "",
        f"All {len(events)} events, oldest first. For git-level time-travel: `git show <sha>:journal/events.jsonl`.",
        "",
    ]
    current_day = None
    for e in events:
        day = e.get("ts", "").split("T")[0]
        if day != current_day:
            lines.append(f"## {day}")
            lines.append("")
            current_day = day
        lines.append(render_event_line(e))
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Fuzzi journal")
    parser.add_argument("--limit", type=int, default=50, help="events on index page")
    args = parser.parse_args()

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events()
    state = load_state()

    (DOCS_DIR / "index.md").write_text(render_index(events, state, args.limit))
    (DOCS_DIR / "by-subject.md").write_text(render_by_subject(events))
    (DOCS_DIR / "archive.md").write_text(render_archive(events))

    print(f"rendered {len(events)} events → {DOCS_DIR}")


if __name__ == "__main__":
    main()
