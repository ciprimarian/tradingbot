# src/agents/reasoning_agent.py

"""
Rule-based Reasoning Agent
Demonstrates AI Reasoning branch with logical rules and inference
Uses forward chaining and rule-based decision making
"""

from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
import pandas as pd
import numpy as np

from src.agents.common import BaseAgent, AgentSignal, SignalType, get_logger


@dataclass
class Rule:
    """Represents a logical rule: IF conditions THEN conclusion"""
    name: str
    conditions: List[Callable]  # list of condition functions that return bool
    conclusion: SignalType
    confidence: float
    priority: int = 0  # higher priority rules fire first
    
    def evaluate(self, context: Dict) -> bool:
        """Check if all conditions are satisfied"""
        return all(condition(context) for condition in self.conditions)


class KnowledgeBase:
    """
    Knowledge base containing trading rules and facts
    Demonstrates knowledge representation and reasoning
    """
    
    def __init__(self):
        self.rules: List[Rule] = []
        self.facts: Dict[str, Any] = {}
        self.logger = get_logger(__name__)
        
    def add_rule(self, rule: Rule):
        """Add a rule to the knowledge base"""
        self.rules.append(rule)
        # Keep sorted by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        
    def add_fact(self, key: str, value: Any):
        """Add a fact to the knowledge base"""
        self.facts[key] = value
        
    def get_fact(self, key: str, default=None):
        """Retrieve a fact"""
        return self.facts.get(key, default)
    
    def clear_facts(self):
        """Clear all facts (usually done each iteration)"""
        self.facts.clear()
    
    def infer(self, context: Dict) -> Optional[Rule]:
        """
        Forward chaining inference
        Find first rule whose conditions are satisfied
        """
        for rule in self.rules:
            if rule.evaluate(context):
                self.logger.debug(f"Rule fired: {rule.name}")
                return rule
        return None


class ReasoningAgent(BaseAgent):
    """
    Agent that uses logical reasoning and rules to make decisions
    
    Demonstrates Reasoning branch:
    - Rule-based systems (IF-THEN rules)
    - Knowledge representation
    - Logical inference (forward chaining)
    - Conflict resolution (priority-based)
    
    Not super sophisticated but shows the core concepts
    """
    
    def __init__(self, name: str = "ReasoningAgent", weight: float = 1.0, config: Optional[Dict] = None):
        super().__init__(name, weight, config)
        
        # Initialize logger
        self.logger = get_logger(self.__class__.__name__)
        
        self.kb = KnowledgeBase()
        self._initialize_rules()
        
        self.logger.info(f"Reasoning agent initialized with {len(self.kb.rules)} rules")
    
    def _initialize_rules(self):
        """
        Define trading rules
        Each rule encodes expert knowledge about trading
        """
        
        # Rule 1: Strong oversold + bullish divergence = BUY
        self.kb.add_rule(Rule(
            name="Oversold_Reversal",
            conditions=[
                lambda ctx: ctx.get('rsi', 50) < 25,
                lambda ctx: ctx.get('price_trend', 0) > 0,  # price rising
                lambda ctx: ctx.get('volume_increasing', False)
            ],
            conclusion=SignalType.STRONG_BUY,
            confidence=0.85,
            priority=10
        ))
        
        # Rule 2: Overbought + volume spike = potential reversal SELL
        self.kb.add_rule(Rule(
            name="Overbought_Reversal",
            conditions=[
                lambda ctx: ctx.get('rsi', 50) > 75,
                lambda ctx: ctx.get('volume_spike', False),
                lambda ctx: ctx.get('price_above_ma', False) is False or ctx.get('ma_divergence', False)
            ],
            conclusion=SignalType.STRONG_SELL,
            confidence=0.85,
            priority=10
        ))
        
        # Rule 3: Golden cross with good volume = BUY
        self.kb.add_rule(Rule(
            name="Golden_Cross",
            conditions=[
                lambda ctx: ctx.get('sma20_above_sma50', False),
                lambda ctx: ctx.get('price_above_ma', False),
                lambda ctx: ctx.get('volume_normal', True)
            ],
            conclusion=SignalType.BUY,
            confidence=0.75,
            priority=8
        ))
        
        # Rule 4: Death cross = SELL
        self.kb.add_rule(Rule(
            name="Death_Cross",
            conditions=[
                lambda ctx: ctx.get('sma20_below_sma50', False),
                lambda ctx: not ctx.get('price_above_ma', True),
                lambda ctx: ctx.get('declining_volume', False) is False  # not declining volume
            ],
            conclusion=SignalType.SELL,
            confidence=0.75,
            priority=8
        ))
        
        # Rule 5: Strong uptrend continuation = BUY
        self.kb.add_rule(Rule(
            name="Trend_Continuation",
            conditions=[
                lambda ctx: ctx.get('consecutive_higher_highs', 0) >= 3,
                lambda ctx: ctx.get('rsi', 50) < 70,  # not overbought
                lambda ctx: ctx.get('volume_increasing', False)
            ],
            conclusion=SignalType.BUY,
            confidence=0.7,
            priority=6
        ))
        
        # Rule 6: Breakdown below support = SELL
        self.kb.add_rule(Rule(
            name="Support_Breakdown",
            conditions=[
                lambda ctx: ctx.get('below_support', False),
                lambda ctx: ctx.get('volume_spike', False)
            ],
            conclusion=SignalType.SELL,
            confidence=0.8,
            priority=9
        ))
        
        # Rule 7: Consolidation after uptrend + low RSI = accumulation BUY
        self.kb.add_rule(Rule(
            name="Consolidation_Accumulation",
            conditions=[
                lambda ctx: ctx.get('low_volatility', False),
                lambda ctx: ctx.get('rsi', 50) < 45,
                lambda ctx: ctx.get('prev_uptrend', False)
            ],
            conclusion=SignalType.BUY,
            confidence=0.65,
            priority=5
        ))
        
        # Rule 8: High volatility + uncertainty = HOLD
        self.kb.add_rule(Rule(
            name="High_Volatility_Hold",
            conditions=[
                lambda ctx: ctx.get('high_volatility', False),
                lambda ctx: 45 <= ctx.get('rsi', 50) <= 55  # neutral RSI
            ],
            conclusion=SignalType.HOLD,
            confidence=0.7,
            priority=4
        ))
    
    def _extract_context(self, data: pd.DataFrame) -> Dict:
        """
        Extract facts from data to create reasoning context
        This is like populating the knowledge base with current observations
        """
        context = {}
        
        if data.empty:
            return context
        
        latest = data.iloc[-1]
        
        # RSI facts
        if 'rsi_14' in data.columns:
            context['rsi'] = latest['rsi_14']
        
        # Moving average facts
        if 'sma_20' in data.columns and 'sma_50' in data.columns:
            context['sma20_above_sma50'] = latest['sma_20'] > latest['sma_50']
            context['sma20_below_sma50'] = latest['sma_20'] < latest['sma_50']
            context['price_above_ma'] = latest['close'] > latest['sma_20']
        
        # Price trend
        if len(data) >= 5:
            recent_returns = data['close'].tail(5).pct_change()
            context['price_trend'] = 1 if recent_returns.sum() > 0 else -1
        
        # Volume facts
        if 'volume' in data.columns and len(data) >= 20:
            avg_volume = data['volume'].tail(20).mean()
            current_volume = latest['volume']
            context['volume_spike'] = current_volume > avg_volume * 1.5
            context['volume_increasing'] = data['volume'].tail(5).is_monotonic_increasing
            context['volume_normal'] = 0.8 * avg_volume < current_volume < 1.2 * avg_volume
            context['declining_volume'] = data['volume'].tail(5).is_monotonic_decreasing
        
        # Volatility facts
        if len(data) >= 20:
            volatility = data['close'].pct_change().tail(20).std()
            avg_volatility = data['close'].pct_change().std()
            context['high_volatility'] = volatility > avg_volatility * 1.5
            context['low_volatility'] = volatility < avg_volatility * 0.7
        
        # Higher highs pattern
        if len(data) >= 10:
            highs = data['high'].tail(10).values
            higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
            context['consecutive_higher_highs'] = higher_highs
        
        # Support level (simple: 20-day low)
        if len(data) >= 20:
            support = data['low'].tail(20).min()
            context['below_support'] = latest['close'] < support * 0.98
        
        # Previous trend
        if len(data) >= 50:
            old_price = data['close'].iloc[-50]
            recent_price = data['close'].iloc[-10]
            context['prev_uptrend'] = recent_price > old_price * 1.05
        
        # MA divergence (price and MA moving different directions)
        if 'sma_20' in data.columns and len(data) >= 5:
            price_dir = data['close'].iloc[-1] - data['close'].iloc[-5]
            ma_dir = data['sma_20'].iloc[-1] - data['sma_20'].iloc[-5]
            context['ma_divergence'] = (price_dir * ma_dir) < 0  # opposite directions
        
        return context
    
    def analyze(self, data: pd.DataFrame, **kwargs) -> AgentSignal:
        """
        Use logical reasoning to generate signal
        Applies forward chaining inference with rules
        """
        if data.empty:
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reasoning="No data for reasoning"
            )
        
        # Extract context from data
        context = self._extract_context(data)
        
        # Log some key facts
        self.logger.debug("Reasoning context:")
        for key, value in list(context.items())[:5]:  # log first 5
            self.logger.debug(f"  {key}: {value}")
        
        # Perform inference - find applicable rule
        fired_rule = self.kb.infer(context)
        
        if fired_rule:
            reasoning = (f"Rule '{fired_rule.name}' fired. "
                        f"Logical inference suggests {fired_rule.conclusion.name}")
            
            return AgentSignal(
                signal_type=fired_rule.conclusion,
                confidence=fired_rule.confidence,
                reasoning=reasoning,
                metadata={
                    'rule_name': fired_rule.name,
                    'rule_priority': fired_rule.priority,
                    'context_size': len(context)
                }
            )
        else:
            # No rule fired - default to HOLD
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.5,
                reasoning="No rules satisfied - defaulting to HOLD",
                metadata={'context_size': len(context)}
            )
