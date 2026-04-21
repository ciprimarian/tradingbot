# Compute lane primer

You work on Fuzzi at `~/Repos/ Local Repos/tradingbot` on branch `dev`. Your machine stays awake — long-running processes and heavy computation belong here.

Your lane is **compute** — the mechanical plumbing, data ingestion, and anything that runs continuously. Judgment choices come from Ciprian; you implement against clear specs and tests.

## What you own

- `src/fuzzi/pit/` — the runtime loop (tick, run, stop)
- `src/fuzzi/runner/` — order lifecycle
- `src/fuzzi/tape/` — data feed wrapper
- `src/fuzzi/blotter/` — JSONL append-only event log
- `src/fuzzi/seatbelt/` — risk/safety checks
- Data ingestion (historical bars from Alpaca → storage)
- Live paper-trading loops (WebSocket feeds, 24/7 processes)
- Parameter sweeps and long backtest batch runs

## What you do NOT touch

- `src/fuzzi/brain/`, `src/fuzzi/regime/`, `src/fuzzi/signals/` — judgment lane owns these
- `tests/` adversarial test design — testing lane owns these (you may add integration tests for your own plumbing)
- Architectural changes without Ciprian's direction

## Before starting any task — CRITICAL

Your dev branch is almost certainly stale. Always run:

```
cd ~/Repos/*Local\ Repos*/tradingbot
git fetch origin
git reset --hard origin/dev
pytest tests/ -v
```

If the test count is lower than `journal/state.json`'s `tests_passing`, something is wrong — stop and report.

Then:
```
tail -n 50 journal/events.jsonl
cat journal/state.json
cat journal/AGENTS.md
```

## Finishing work

Every delivered change:

1. Run the full test suite green: `pytest tests/ -v`.
2. Append events to `journal/events.jsonl` (kind: `done`).
3. Update `journal/state.json` — update `tests_passing`, move finished items out of `now`.
4. Run `python journal/render.py`.
5. Commit everything in one go.
6. `git push origin dev`.

## Entry style

- Never reference "I", "we", "Codex", or any agent name in commits or journal entries.
- Describe the work: "wire NerveTracker into pit" not "Codex wired NerveTracker".
- Commit messages in lowercase imperative.

## Current assignment

**Phase 3: Replace the pit's raw `self.nerve: float` with the real `NerveTracker`.**

File: `src/fuzzi/pit/loop.py`
- Import `NerveTracker` from `src.fuzzi.nerve`.
- Replace `self.nerve: float = 0.5` with `self.nerve = NerveTracker()`.
- Replace `self._nudge_nerve(0.03)` calls with `self.nerve.record_win(source.name)`.
- Replace `self._nudge_nerve(-0.05)` calls with `self.nerve.record_rejection(source.name)` (or `record_loss` if pnl is known).
- Replace `sizing_multiplier = 0.5 if self.nerve < 0.3 else 1.0` with `sizing_multiplier = self.nerve.sizing_multiplier`.
- In `_log_tick`, change nerve field to `self.nerve.state().global_nerve` and notes to `self.nerve.state().summary()`.
- Remove the `_nudge_nerve` helper entirely.

File: `tests/test_pit.py`
- `test_nerve_moves_with_rejections_and_approvals`: assert on `pit.nerve.state().global_nerve` with approximate checks (EWMA smooths values).
- `test_low_nerve_halves_position_sizing`: set nerve low by repeated `pit.nerve.record_loss("test", pnl=-50)` instead of `pit.nerve = 0.25`. Update expected quantity based on new sizing curve.

Acceptance: all 46 existing tests pass, plus updated assertions on the two tests above.

After Phase 3 lands, likely next: Alpaca historical data ingestion for backtests (compute lane, remote-friendly).
