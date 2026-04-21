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

## pit.nerve

- `2026-04-22` ✗ wiring NerveTracker into Pit blocked on compute-lane rebase to latest dev

## regime.classify

- `2026-04-22` • open — thresholds that map (efficiency_ratio, volatility, direction) → regime + confidence need to be chosen

## workflow.branches

- `2026-04-21` ◆ minimal branches: main (production-ready), dev (active work), data (archive). All three agents commit to dev.

## workflow.journal

- `2026-04-22` ◆ knowledge base = events.jsonl (source of truth) + state.json (current) + rendered markdown for GH Pages. Git provides versioning; tree-at-any-point via git show.

## workflow.lanes

- `2026-04-22` ◆ three-agent split: compute lane (heavy continuous work, remote box), judgment lane (brain/signals/design, local), testing lane (adversarial tests, backtests, validation).

