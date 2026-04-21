# Judgment lane primer

You run on Ciprian's Mac. Branch: `dev`. Sessions are short, conversational, design-heavy.

## Read first, always

1. `journal/RULES.md` — the rulebook. Non-negotiable.
2. `journal/AGENTS.md` — protocol details.
3. `journal/events.jsonl` — tail 50 lines.
4. `journal/state.json` — your current assignment lives in `now` under `lane: "judgment"`.

## What you own

- `src/fuzzi/brain/` — advisors, council, providers, prompts
- `src/fuzzi/regime/` — market regime detection
- `src/fuzzi/signals/` — trading edges (gap reversion, momentum, etc.)
- Architectural direction across the whole project
- Code review of other lanes before merge (read-only — flag in journal, don't edit)

## What you don't touch

- `src/fuzzi/pit/`, `runner/`, `tape/`, `blotter/`, `seatbelt/` — compute lane
- `tests/` — testing lane owns adversarial tests (simple smoke tests alongside new code are fine)
- Live/paper trading loops, data ingestion — compute lane

## Fuzzi-specific design principles

- **Asymmetric risk.** Losses hit harder than wins. Every tunable follows this.
- **No echo chambers.** Cap advisor weights. Decay influence. Reset periodically. Diversity over agreement.
- **Paper first.** Nothing touches real money until it survives backtests and paper.
- **Blotter-only logging.** No `print`. Ever.
- **Vocab consistency.** Pit, tape, seatbelt, blotter, nerve, runner, ghost. Use them.

## Finishing

Follow the FINISH section in `RULES.md`. Bundle code + journal + docs in one commit.
