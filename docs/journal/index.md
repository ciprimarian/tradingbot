# Fuzzi Journal

What happened, what's happening, what's next. Source of truth is `journal/events.jsonl` — this page is rendered from it.

## Right now

- **regime.classify** `judgment` — classify logic (thresholds → regime) open as TODO in src/fuzzi/regime/detector.py
- **pit.portfolio** `compute` — replace static $100 portfolio snapshot with updated cash and positions so seatbelt sizes against reality
- **tests.findings.resolution** `judgment` — judgment lane to decide: (1) gap reversion fill model — same-day entry vs multi-bar hold; (2) council MAJORITY threshold calibration; (3) global vs per-strategy nerve pool design

## Up next

- fix NaN confidence propagation in AdvisorVerdict.score (guard in score property)
- wire regime detector into pit once _classify is implemented
- add momentum signal source as second edge alongside gap reversion
- first paper-trade dry run on SPY with gap reversion + nerve + brain
- alpaca live tape WebSocket ingestion (compute lane)
- add @pytest.mark.integration to legacy Alpaca tests

## Recent activity

### 2026-04-22

- `08:00` ◆ **workflow.lanes** — three-agent split: compute lane (heavy continuous work, remote box), judgment lane (brain/signals/design, local), testing lane (adversarial tests, backtests, validation).
- `08:00` ◆ **workflow.journal** — knowledge base = events.jsonl (source of truth) + state.json (current) + rendered markdown for GH Pages. Git provides versioning; tree-at-any-point via git show.
- `08:30` ✓ **fuzzi.regime** — regime detector scaffolded: efficiency_ratio + volatility indicators, five regimes (TRENDING_UP/DOWN, CHOPPY, CALM, VOLATILE). _classify logic left as open TODO.
- `08:30` • **regime.classify** — open — thresholds that map (efficiency_ratio, volatility, direction) → regime + confidence need to be chosen
- `08:30` ✗ **pit.nerve** — wiring NerveTracker into Pit blocked on compute-lane rebase to latest dev (since resolved)
- `09:30` ◆ **stack.language** — stay Python. LLM latency dominates critical path; compute is microseconds. Escalation: NumPy → Numba → Cython → PyO3, one rung at a time.
- `09:30` ◆ **workflow.voice** — no AI-speak. simple, concise, direct. no corporate hedging, no motivational-poster sentences.
- `09:30` ✓ **journal.rules** — RULES.md added — short-form rulebook every agent reads on session start.
- `09:30` ✓ **journal.primers** — primers stripped of volatile sections; assignments now live only in state.json.now keyed by lane.

### 2026-04-21

- `00:00` ◆ **workflow.branches** — minimal branches: main (production-ready), dev (active work), data (archive). All three agents commit to dev.
- `22:15` ✓ **pit.nerve** — pit now uses NerveTracker for sizing, tick summaries, and rejection/win updates; pit tests updated for EWMA behavior `[f90bb22]`
- `22:22` · **tests.bootstrap** — conftest.py added: stubs ALPACA_API_KEY/SECRET env vars so tests collect without live credentials; exposes two pre-existing legacy integration tests (test_brokers::test_connection, test_strategies::test_data_fetch_and_strategy) that hit real Alpaca endpoints — fail with 401, not a new regression
- `22:22` ✓ **tests.adversarial** — adversarial tests for regime detector: 44 tests covering UNKNOWN path (empty/short bars), _efficiency_ratio and _return_volatility directly (boundary values, flat/spike/zigzag/zero/negative/extreme prices), adversarial observe() edge cases asserting only NotImplementedError propagates, and 10 contract tests that skip until _classify lands `[a4b29d5]`
- `22:57` ✓ **pit.feedback** — nerve no longer records wins on seatbelt approval; realized pnl updates flow through pit.record_outcome and blotter outcome entries
- `23:15` ✓ **tests.adversarial** — six adversarial test batches added (council, signals, seatbelt, backtest, nerve, blotter+runner): 157 new tests, 7 xfail documenting real bugs — NaN score propagation in AdvisorVerdict, 2v1 majority conviction collapse, sizing_multiplier=0 override by seatbelt floor, gap reversion zero win-rate under next-bar fill model, inverted regime preference, global nerve cratering from single strategy `[5defe6e]`
- `23:15` · **tests.findings** — critical: gap reversion win rate=0% in choppy market — next-bar fill misses reversion; strategy needs same-day entry or multi-bar hold. NaN confidence in AdvisorVerdict propagates to council conviction. 2v1 MAJORITY with max confidence falls below conviction threshold (0.18 < 0.40). Global nerve shares pool across strategies — one bad strategy suppresses all trading.

### 2026-04-20

- `15:42` ◆ **fuzzi.philosophy** — rebuild as Fuzzi — money-is-fuzzy, flow-is-real. Paper trading first, nothing ships to live.
- `15:42` ✓ **fuzzi.spine** — created core: config, blotter, seatbelt, runner, common models `[ebef227]`
- `17:55` ✓ **fuzzi.pit** — pit runtime loop wired — signal sources → seatbelt → runner, tape feed scaffold `[0e1489d]`
- `18:17` ✓ **fuzzi.brain** — brain layer: Advisor + Council with weighted consensus, MockProvider for tests `[ec88373]`
- `18:25` ✓ **fuzzi.pit** — pit consults brain + council gate before seatbelt `[0584bee]`
- `18:54` ◆ **brain.council** — weight caps 0.5x-1.5x, exponential decay 0.9, reset every 30 rulings. Prevents echo chamber and single-model dominance.
- `18:54` ✓ **brain.providers** — OpenClawProvider added; unanimous boost reduced from 1.2x to 1.1x `[bffb9a3]`
- `19:00` ◆ **brain.auth** — primary LLM access via Codex CLI OAuth tokens (~/.codex/auth.json) — free via ChatGPT Plus, paid APIs only as fallback
- `19:00` ✓ **brain.providers** — CodexOAuthProvider implemented with auto-refresh on 401 `[fbb851f]`
- `20:21` ✓ **fuzzi.nerve** — NerveTracker: EWMA decay 0.85, win_boost 0.08, loss_penalty 0.12, asymmetric risk, per-strategy + global `[f218760]`
- `20:50` ✓ **fuzzi.config** — LLMSettings added; brain can locate auth.json and model defaults `[ad70c89]`
- `20:57` ✓ **fuzzi.merge** — pit/tape/signals merged with brain layer; CouncilGate separated from LLM Council `[73692e2]`

## Legend

- `✓ done` — delivered
- `• now` — in flight
- `○ plan` — queued
- `◆ decide` — architectural decision
- `✗ blocked` — waiting on something
- `· note` — observation

_Rendered 2026-04-21 23:11 UTC from 28 events._
