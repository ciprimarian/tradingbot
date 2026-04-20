"""
The Council — aggregates advisor verdicts into a final ruling.

This is where multi-LLM consensus happens. Three advisors give their take,
the council weighs them by confidence, track record, and role relevance,
then produces a single ruling: act or don't.

The council doesn't just vote — it detects disagreement patterns:
- All agree → high confidence ruling
- 2v1 split → moderate confidence, flag the dissent
- All disagree → HOLD, something's unclear
- One abstains → ruling from remaining two
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from src.fuzzi.brain.advisor import Advisor, AdvisorVerdict, Stance, STANCE_SCORES


class RulingAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class DissentPattern(str, Enum):
    UNANIMOUS = "unanimous"  # all advisors agree
    MAJORITY = "majority"  # 2v1
    SPLIT = "split"  # no clear majority
    DEADLOCK = "deadlock"  # equal opposing forces
    SPARSE = "sparse"  # too many abstains to decide


@dataclass(slots=True)
class CouncilRuling:
    action: RulingAction
    conviction: float  # 0-1, how strong the ruling is
    dissent: DissentPattern
    reasoning: str
    verdicts: list[AdvisorVerdict]
    nerve_adjustment: float  # how much this ruling should move the nerve
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def should_act(self) -> bool:
        """Only act on buy/sell with sufficient conviction."""
        return self.action != RulingAction.HOLD and self.conviction >= 0.4


class Council:
    """
    Aggregates advisor verdicts into actionable rulings.

    The council is opinionated:
    - Unanimous agreement gets a conviction boost
    - Dissent reduces conviction
    - Strategist (Opus) gets veto power on high-risk situations
    - If the scout (Grok) flags unusual social activity, conviction caps at 0.6
      (social momentum can be manipulated)
    """

    def __init__(
        self,
        advisors: list[Advisor],
        conviction_threshold: float = 0.4,
        strategist_veto_threshold: float = -0.5,
    ) -> None:
        self.advisors = advisors
        self.conviction_threshold = conviction_threshold
        self.strategist_veto_threshold = strategist_veto_threshold

    def rule(self, verdicts: list[AdvisorVerdict]) -> CouncilRuling:
        """
        Produce a ruling from collected verdicts.

        Scoring:
        1. Each verdict contributes: stance_score × confidence × adaptive_weight
        2. Sum the weighted scores
        3. Normalize to [-1, 1]
        4. Apply dissent penalty
        5. Check for strategist veto
        """
        if not verdicts:
            return CouncilRuling(
                action=RulingAction.HOLD,
                conviction=0.0,
                dissent=DissentPattern.SPARSE,
                reasoning="no verdicts received",
                verdicts=[],
                nerve_adjustment=0.0,
            )

        # Filter out abstains for scoring
        active = [v for v in verdicts if v.stance != Stance.ABSTAIN]

        if len(active) < 2:
            return CouncilRuling(
                action=RulingAction.HOLD,
                conviction=0.0,
                dissent=DissentPattern.SPARSE,
                reasoning="too few active verdicts to decide",
                verdicts=verdicts,
                nerve_adjustment=-0.02,
            )

        # Calculate weighted aggregate score
        advisor_map = {a.name: a for a in self.advisors}
        total_weight = 0.0
        weighted_score = 0.0

        for v in active:
            advisor = advisor_map.get(v.advisor_name)
            w = advisor.adaptive_weight if advisor else 0.33
            weighted_score += v.score * w
            total_weight += w

        if total_weight == 0:
            normalized = 0.0
        else:
            normalized = weighted_score / total_weight  # [-1, 1]

        # Determine dissent pattern
        dissent = self._detect_dissent(active)

        # Conviction: absolute strength of normalized score, penalized by dissent
        raw_conviction = abs(normalized)
        dissent_penalty = {
            DissentPattern.UNANIMOUS: 0.0,
            DissentPattern.MAJORITY: 0.15,
            DissentPattern.SPLIT: 0.35,
            DissentPattern.DEADLOCK: 0.5,
            DissentPattern.SPARSE: 0.4,
        }
        conviction = max(0.0, raw_conviction - dissent_penalty[dissent])

        # Unanimous boost
        if dissent == DissentPattern.UNANIMOUS:
            conviction = min(1.0, conviction * 1.2)

        # Strategist veto: if strategist strongly opposes what others want
        strategist_verdicts = [v for v in active if v.role.value == "strategist"]
        non_strategist = [v for v in active if v.role.value != "strategist"]
        vetoed = False
        if strategist_verdicts and non_strategist:
            strat_score = strategist_verdicts[0].score
            others_direction = sum(v.score for v in non_strategist) / len(non_strategist)
            # Strategist strongly opposes the direction others want
            if others_direction > 0.2 and strat_score < self.strategist_veto_threshold:
                vetoed = True
            elif others_direction < -0.2 and strat_score > -self.strategist_veto_threshold:
                vetoed = True

        # Scout social flag: cap conviction if scout flagged manipulation risk
        scout_verdicts = [v for v in active if v.role.value == "scout"]
        social_capped = False
        if scout_verdicts:
            for sv in scout_verdicts:
                if any("manipulation" in f.lower() or "pump" in f.lower() for f in sv.flags):
                    conviction = min(conviction, 0.5)
                    social_capped = True

        # Determine action
        if vetoed:
            action = RulingAction.HOLD
            reasoning = "strategist vetoed — risk too high"
            nerve_adj = -0.05
        elif conviction < self.conviction_threshold:
            action = RulingAction.HOLD
            reasoning = "conviction too low to act"
            nerve_adj = -0.01
        elif normalized > 0:
            action = RulingAction.BUY
            reasoning = self._build_reasoning(active, "buy", dissent, social_capped)
            nerve_adj = 0.02
        else:
            action = RulingAction.SELL
            reasoning = self._build_reasoning(active, "sell", dissent, social_capped)
            nerve_adj = 0.02

        return CouncilRuling(
            action=action,
            conviction=round(conviction, 3),
            dissent=dissent,
            reasoning=reasoning,
            verdicts=verdicts,
            nerve_adjustment=nerve_adj,
            metadata={
                "normalized_score": round(normalized, 4),
                "raw_conviction": round(raw_conviction, 4),
                "vetoed": vetoed,
                "social_capped": social_capped,
                "active_count": len(active),
            },
        )

    def _detect_dissent(self, active: list[AdvisorVerdict]) -> DissentPattern:
        """Classify the agreement pattern among active verdicts."""
        if len(active) < 2:
            return DissentPattern.SPARSE

        directions = []
        for v in active:
            score = STANCE_SCORES[v.stance]
            if score > 0.1:
                directions.append("bull")
            elif score < -0.1:
                directions.append("bear")
            else:
                directions.append("flat")

        unique = set(directions)
        if len(unique) == 1:
            return DissentPattern.UNANIMOUS

        bull_count = directions.count("bull")
        bear_count = directions.count("bear")

        if bull_count >= 2 or bear_count >= 2:
            return DissentPattern.MAJORITY

        if bull_count == bear_count and bull_count > 0:
            return DissentPattern.DEADLOCK

        return DissentPattern.SPLIT

    def _build_reasoning(
        self,
        active: list[AdvisorVerdict],
        direction: str,
        dissent: DissentPattern,
        social_capped: bool,
    ) -> str:
        """Build a concise reasoning string from the verdict landscape."""
        parts = [f"council says {direction}"]

        if dissent == DissentPattern.UNANIMOUS:
            parts.append("all advisors agree")
        elif dissent == DissentPattern.MAJORITY:
            dissenters = [v.advisor_name for v in active if (
                (direction == "buy" and v.score < 0) or
                (direction == "sell" and v.score > 0)
            )]
            if dissenters:
                parts.append(f"{', '.join(dissenters)} dissents")

        if social_capped:
            parts.append("conviction capped — social manipulation flag")

        return " — ".join(parts)
