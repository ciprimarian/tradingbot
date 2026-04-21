# Agent protocol

Fuzzi is built by three agents working in parallel. This document is the rulebook.
All three agents: read this on every session start.

## The knowledge base

Everything that was done, is being done, or is planned lives here:

| File | Purpose | Edit mode |
|------|---------|-----------|
| `journal/events.jsonl` | what happened — source of truth | append-only |
| `journal/state.json` | what's live and what's queued | edit in place |
| `docs/journal/*.md` | rendered human-readable views | **never edit** (build artifacts) |

Never reference other agents, "I", or "we" in entries. Describe the work, not the doer.

## Event schema

Each line in `events.jsonl` is one JSON object:

```json
{"ts":"2026-04-22T08:30:00Z","kind":"done","subject":"fuzzi.regime","text":"scaffolded detector with efficiency ratio and volatility indicators","commit":"abc1234"}
```

| Field | Required | Values |
|-------|----------|--------|
| `ts` | yes | ISO 8601 UTC |
| `kind` | yes | `done`, `now`, `plan`, `decide`, `blocked`, `note` |
| `subject` | yes | dotted identifier, e.g. `brain.council`, `pit.nerve`, `workflow.lanes` |
| `text` | yes | one short factual line |
| `commit` | optional | git sha if the event corresponds to a commit |
| `refs` | optional | list of related subjects or shas |

## Entry protocol

**On starting work:**
1. `tail -n 50 journal/events.jsonl` — see what's recent
2. `cat journal/state.json` — see what's live
3. Read the primer for your lane: `journal/primers/<lane>.md`

**On finishing work:**
1. Append one JSON line per completed subject to `journal/events.jsonl`
2. Update `journal/state.json` — move completed items out of `now`, pull next items in
3. Run `python journal/render.py` to regenerate the docs
4. Commit everything together: code + journal + docs

## Lanes

Each agent owns one lane. Don't edit files outside your lane without coordination.

| Lane | What it owns | Primer |
|------|-------------|--------|
| judgment | `src/fuzzi/brain/`, `src/fuzzi/regime/`, `src/fuzzi/signals/` — design + strategy | `journal/primers/judgment.md` |
| compute | `src/fuzzi/pit/`, `src/fuzzi/runner/`, `src/fuzzi/tape/`, `src/fuzzi/blotter/`, `src/fuzzi/seatbelt/`, data ingestion, live loops | `journal/primers/compute.md` |
| testing | `tests/` + adversarial test design, backtest validation, reports | `journal/primers/testing.md` |

Shared (any lane may touch, coordinate first):
`src/fuzzi/__init__.py`, `src/fuzzi/common/`, `src/fuzzi/config/`, `journal/`, `docs/`, `mkdocs.yml`.

## Branch rules

- All work lands on `dev`.
- Never commit to `main` directly. `main` gets updates only via merged, green, reviewed changes.
- `data` is a frozen archive branch — do not touch.
- Always `git fetch origin && git reset --hard origin/dev` before starting, if your local dev is stale.

## Commit style

- One-line summary in lowercase, imperative ("add regime classifier", not "Added" or "Adds").
- Never include "Co-Authored-By: Claude" or any agent attribution — all commits are on Ciprian's behalf.
- Bundle related work into single commits; avoid noise commits.

## What does NOT go in the journal

- Chat transcripts — those stay in each tool's own session store.
- Secrets, API keys — `.env` and `.gitignore` handle those.
- Full design docs — those live in `docs/` as their own pages and get referenced by subject.
- File contents or long code snippets — the journal points *at* the code, not *to* it.
