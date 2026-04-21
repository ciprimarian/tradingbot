# Journal by subject

Every event grouped by the subsystem it touches.

## brain.auth

- `2026-04-20` ◆ primary LLM access via Codex CLI OAuth tokens (~/.codex/auth.json) — free via ChatGPT Plus, paid APIs only as fallback

## brain.council

- `2026-04-20` ◆ weight caps 0.5x-1.5x, exponential decay 0.9, reset every 30 rulings. Prevents echo chamber and single-model dominance.

## brain.providers

- `2026-04-20` ✓ OpenClawProvider added; unanimous boost reduced from 1.2x to 1.1x `[bffb9a3]`
- `2026-04-20` ✓ CodexOAuthProvider implemented with auto-refresh on 401 `[fbb851f]`

## fuzzi.brain

- `2026-04-20` ✓ brain layer: Advisor + Council with weighted consensus, MockProvider for tests `[ec88373]`

## fuzzi.config

- `2026-04-20` ✓ LLMSettings added; brain can locate auth.json and model defaults `[ad70c89]`

## fuzzi.merge

- `2026-04-20` ✓ pit/tape/signals merged with brain layer; CouncilGate separated from LLM Council `[73692e2]`

## fuzzi.nerve

- `2026-04-20` ✓ NerveTracker: EWMA decay 0.85, win_boost 0.08, loss_penalty 0.12, asymmetric risk, per-strategy + global `[f218760]`

## fuzzi.philosophy

- `2026-04-20` ◆ rebuild as Fuzzi — money-is-fuzzy, flow-is-real. Paper trading first, nothing ships to live.

## fuzzi.pit

- `2026-04-20` ✓ pit runtime loop wired — signal sources → seatbelt → runner, tape feed scaffold `[0e1489d]`
- `2026-04-20` ✓ pit consults brain + council gate before seatbelt `[0584bee]`

## fuzzi.regime

- `2026-04-22` ✓ regime detector scaffolded: efficiency_ratio + volatility indicators, five regimes (TRENDING_UP/DOWN, CHOPPY, CALM, VOLATILE). _classify logic left as open TODO.

## fuzzi.spine

- `2026-04-20` ✓ created core: config, blotter, seatbelt, runner, common models `[ebef227]`

## journal.primers

- `2026-04-22` ✓ primers stripped of volatile sections; assignments now live only in state.json.now keyed by lane.

## journal.rules

- `2026-04-22` ✓ RULES.md added — short-form rulebook every agent reads on session start.

## pit.feedback

- `2026-04-21` ✓ nerve no longer records wins on seatbelt approval; realized pnl updates flow through pit.record_outcome and blotter outcome entries

## pit.nerve

- `2026-04-21` ✓ pit now uses NerveTracker for sizing, tick summaries, and rejection/win updates; pit tests updated for EWMA behavior `[f90bb22]`
- `2026-04-22` ✗ wiring NerveTracker into Pit blocked on compute-lane rebase to latest dev (since resolved)

## regime.classify

- `2026-04-22` • open — thresholds that map (efficiency_ratio, volatility, direction) → regime + confidence need to be chosen

## stack.language

- `2026-04-22` ◆ stay Python. LLM latency dominates critical path; compute is microseconds. Escalation: NumPy → Numba → Cython → PyO3, one rung at a time.

## tests.adversarial

- `2026-04-21` ✓ adversarial tests for regime detector: 44 tests covering UNKNOWN path (empty/short bars), _efficiency_ratio and _return_volatility directly (boundary values, flat/spike/zigzag/zero/negative/extreme prices), adversarial observe() edge cases asserting only NotImplementedError propagates, and 10 contract tests that skip until _classify lands `[a4b29d5]`
- `2026-04-21` ✓ six adversarial test batches added (council, signals, seatbelt, backtest, nerve, blotter+runner): 157 new tests, 7 xfail documenting real bugs — NaN score propagation in AdvisorVerdict, 2v1 majority conviction collapse, sizing_multiplier=0 override by seatbelt floor, gap reversion zero win-rate under next-bar fill model, inverted regime preference, global nerve cratering from single strategy `[5defe6e]`

## tests.bootstrap

- `2026-04-21` · conftest.py added: stubs ALPACA_API_KEY/SECRET env vars so tests collect without live credentials; exposes two pre-existing legacy integration tests (test_brokers::test_connection, test_strategies::test_data_fetch_and_strategy) that hit real Alpaca endpoints — fail with 401, not a new regression

## tests.findings

- `2026-04-21` · critical: gap reversion win rate=0% in choppy market — next-bar fill misses reversion; strategy needs same-day entry or multi-bar hold. NaN confidence in AdvisorVerdict propagates to council conviction. 2v1 MAJORITY with max confidence falls below conviction threshold (0.18 < 0.40). Global nerve shares pool across strategies — one bad strategy suppresses all trading.

## workflow.branches

- `2026-04-21` ◆ minimal branches: main (production-ready), dev (active work), data (archive). All three agents commit to dev.

## workflow.journal

- `2026-04-22` ◆ knowledge base = events.jsonl (source of truth) + state.json (current) + rendered markdown for GH Pages. Git provides versioning; tree-at-any-point via git show.

## workflow.lanes

- `2026-04-22` ◆ three-agent split: compute lane (heavy continuous work, remote box), judgment lane (brain/signals/design, local), testing lane (adversarial tests, backtests, validation).

## workflow.voice

- `2026-04-22` ◆ no AI-speak. simple, concise, direct. no corporate hedging, no motivational-poster sentences.

