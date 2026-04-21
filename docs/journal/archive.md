# Full chronology

All 18 events, oldest first. For git-level time-travel: `git show <sha>:journal/events.jsonl`.

## 2026-04-20

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
## 2026-04-21

- `00:00` ◆ **workflow.branches** — minimal branches: main (production-ready), dev (active work), data (archive). All three agents commit to dev.
## 2026-04-22

- `08:00` ◆ **workflow.lanes** — three-agent split: compute lane (heavy continuous work, remote box), judgment lane (brain/signals/design, local), testing lane (adversarial tests, backtests, validation).
- `08:00` ◆ **workflow.journal** — knowledge base = events.jsonl (source of truth) + state.json (current) + rendered markdown for GH Pages. Git provides versioning; tree-at-any-point via git show.
- `08:30` ✓ **fuzzi.regime** — regime detector scaffolded: efficiency_ratio + volatility indicators, five regimes (TRENDING_UP/DOWN, CHOPPY, CALM, VOLATILE). _classify logic left as open TODO.
- `08:30` • **regime.classify** — open — thresholds that map (efficiency_ratio, volatility, direction) → regime + confidence need to be chosen
- `08:30` ✗ **pit.nerve** — wiring NerveTracker into Pit blocked on compute-lane rebase to latest dev

