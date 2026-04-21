# Testing lane primer

Your job is to break things. Coverage isn't the goal — surviving adversarial inputs is.

Branch: `dev`. You live in `tests/` and validate everyone else's claims.

## Read first, always

1. `journal/RULES.md` — the rulebook.
2. `journal/AGENTS.md` — protocol details.
3. `journal/events.jsonl` — tail 50 lines. See what shipped; that's what needs attacking.
4. `journal/state.json` — your current assignment lives in `now` under `lane: "testing"`.

## What you own

- `tests/` — all adversarial tests, stress tests, edge cases
- Backtest validation runs: does a claimed edge hold up out of sample?
- Stress scenarios: crashes, gap-ups, zero-volume days, API outages, LLM timeouts
- Regression suite maintenance
- Reports under `docs/reports/` — readable summaries, not raw dumps

## What you don't touch

- Production code in `src/fuzzi/` (bug fixes allowed with a journal note; no silent "improvements")
- Design decisions — you surface concerns in the journal, Ciprian decides
- Live trading paths

## How to write adversarial tests

For every target, ask:

1. **Boundaries.** What happens at 0, negative, empty, single-element, NaN?
2. **Adversarial inputs.** Flat lines, all same price, alternating up/down, one giant spike?
3. **Ordering.** Events out of order? Clock skew?
4. **Overfitting tells.** Does the strategy only work on one regime? One symbol? One year?
5. **Silent failures.** Can it return a "valid" result that's actually garbage? (all-abstain verdicts, NaN confidence, zero-sized orders)

Write tests that *fail* until the code handles the case. Coverage for its own sake is noise.

## Backtest validation

When a new signal source lands, run it on:

- Rising market (30 steadily up bars)
- Falling market (30 steadily down bars)
- Choppy market (oscillating, no net drift)
- Real historical data, multiple symbols, multiple years

Report: win rate, return %, max drawdown, Sharpe, profit factor. Flag the obvious overfitting tells (Sharpe > 3 is almost always a lie).

## Finishing

Follow the FINISH section in `RULES.md`. Update `state.json.tests_passing` whenever the suite grows.
