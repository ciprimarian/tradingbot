# Fuzzi Journal

What happened, what's happening, what's next. Source of truth is `journal/events.jsonl` — this page is rendered from it.

## Right now

- **regime.classify** `judgment` — classify logic (thresholds → regime) open as TODO in src/fuzzi/regime/detector.py
- **tests.brain** `testing` — stress-test brain Council under degenerate advisor outputs (all abstain, all extreme, one NaN confidence)
- **backtest.ingestion** `compute` — historical Alpaca bars → parquet storage for backtests

## Up next

- wire regime detector into pit (regime gates which signal sources fire)
- add momentum signal source as second edge alongside gap reversion
- first paper-trade dry run on SPY with gap reversion + nerve + brain
- alpaca live tape WebSocket ingestion (compute lane)

## Recent activity

### 2026-04-22

- `08:00` ◆ **workflow.lanes** — three-agent split: compute lane (heavy continuous work, remote box), judgment lane (brain/signals/design, local), testing lane (adversarial tests, backtests, validation).
- `08:00` ◆ **workflow.journal** — knowledge base = events.jsonl (source of truth) + state.json (current) + rendered markdown for GH Pages. Git provides versioning; tree-at-any-point via git show.
- `08:30` ✓ **fuzzi.regime** — regime detector scaffolded: efficiency_ratio + volatility indicators, five regimes (TRENDING_UP/DOWN, CHOPPY, CALM, VOLATILE). _classify logic left as open TODO.
- `08:30` • **regime.classify** — open — thresholds that map (efficiency_ratio, volatility, direction) → regime + confidence need to be chosen
- `08:30` ✗ **pit.nerve** — wiring NerveTracker into Pit blocked on compute-lane rebase to latest dev

### 2026-04-21

- `00:00` ◆ **workflow.branches** — minimal branches: main (production-ready), dev (active work), data (archive). All three agents commit to dev.
- `22:15` ✓ **pit.nerve** — pit now uses NerveTracker for sizing, tick summaries, and rejection/win updates; pit tests updated for EWMA behavior
- `22:22` · **tests.bootstrap** — conftest.py added: stubs ALPACA_API_KEY/SECRET env vars so tests collect without live credentials; exposes two pre-existing legacy integration tests (test_brokers::test_connection, test_strategies::test_data_fetch_and_strategy) that hit real Alpaca endpoints — fail with 401, not a new regression
- `22:22` ✓ **tests.adversarial** — adversarial tests for regime detector: 44 tests covering UNKNOWN path (empty/short bars), _efficiency_ratio and _return_volatility directly (boundary values, flat/spike/zigzag/zero/negative/extreme prices), adversarial observe() edge cases asserting only NotImplementedError propagates, and 10 contract tests that skip until _classify lands then lock in the regime mapping `[f31664a]`

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

_Rendered 2026-04-21 22:24 UTC from 21 events._
