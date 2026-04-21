# Compute lane primer

You run on `omathink` (stays awake). Repo: `~/Repos/ Local Repos/tradingbot`. Branch: `dev`.

Your machine doesn't sleep. Long processes and heavy computation belong here. Judgment choices come from Ciprian; you implement against clean specs and tests.

## Read first, always

1. `journal/RULES.md` — the rulebook.
2. `journal/AGENTS.md` — protocol details.
3. `journal/events.jsonl` — tail 50 lines.
4. `journal/state.json` — your current assignment lives in `now` under `lane: "compute"`.

## Critical: sync your dev before every session

Your local `dev` goes stale faster than anyone else's because you're on a remote box.

```
cd ~/Repos/*Local\ Repos*/tradingbot
git fetch origin
git reset --hard origin/dev
pytest tests/ -v
```

Test count lower than `state.json.tests_passing`? Stop. Something's wrong.

## What you own

- `src/fuzzi/pit/` — runtime loop (tick, run, stop)
- `src/fuzzi/runner/` — order lifecycle
- `src/fuzzi/tape/` — data feed wrapper
- `src/fuzzi/blotter/` — JSONL append-only event log
- `src/fuzzi/seatbelt/` — risk/safety checks
- Alpaca integration: historical data ingestion, live paper-trading loop
- Parameter sweeps, batch backtests, anything long-running

## What you don't touch

- `src/fuzzi/brain/`, `regime/`, `signals/` — judgment lane
- Adversarial tests in `tests/` — testing lane (integration tests for your own plumbing are fine)
- Architectural changes without Ciprian's say-so

## Finishing

Follow the FINISH section in `RULES.md`. Update `state.json.tests_passing` if it changes.
