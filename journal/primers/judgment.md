# Judgment lane primer

You work on Fuzzi at `~/Repos/tradingbot` (or equivalent) on branch `dev`.

Your lane is **judgment** — the parts of the system that require design choices, trade-offs, and taste rather than raw compute. Keep sessions short and conversational with Ciprian; return design + code for the brain, regime, and signal layers.

## What you own

- `src/fuzzi/brain/` — advisors, council, providers, prompts
- `src/fuzzi/regime/` — market regime detection
- `src/fuzzi/signals/` — trading edges (gap reversion, future momentum/mean-reversion)
- Architectural decisions across the whole project
- Code review of other lanes before merge

## What you do NOT touch

- `src/fuzzi/pit/`, `src/fuzzi/runner/`, `src/fuzzi/tape/`, `src/fuzzi/blotter/`, `src/fuzzi/seatbelt/` — compute lane owns these
- `tests/` directory contents — testing lane writes tests (you may write simple smoke tests alongside new judgment code, but adversarial tests belong to testing)
- Live/paper trading loops, data ingestion — compute lane

## Before starting any task

```
git fetch origin && git reset --hard origin/dev
tail -n 50 journal/events.jsonl
cat journal/state.json
cat journal/AGENTS.md
```

## Finishing work

Every delivered change:

1. Append one event per subject to `journal/events.jsonl` (kind: `done`).
2. Update `journal/state.json` — remove finished items from `now`, add new open items.
3. Run `python journal/render.py` to regenerate `docs/journal/*.md`.
4. Commit everything in one go: `git add src/fuzzi journal/ docs/journal/ && git commit -m "..."`.
5. `git push origin dev`.

## Entry style

- Never reference "I", "we", "Claude", or any agent name in commits or journal entries.
- Describe the work: "add regime classifier" not "I added the regime classifier".
- Commit messages in lowercase imperative.

## Current state

Read `journal/state.json` for the live list. As of the last update:

- **Open TODO:** `src/fuzzi/regime/detector.py` — `_classify()` method (thresholds → regime + confidence). Personality decision.
- **Tests passing:** 46 (run `pytest tests/ -v`).
- **Next candidates:** wire regime into pit, add momentum signal source, prompt refinement for brain advisors.

## Design principles (Fuzzi-specific)

- Asymmetric risk: penalize losses more than rewards.
- Prevent echo chambers: cap weights, decay influence, reset periodically.
- Paper first: no code path touches real money until validated.
- Blotter-only logging: no prints; everything goes through `JsonlBlotter`.
- Vocabulary: pit, tape, seatbelt, blotter, runner, nerve, ghost. Use these consistently.
