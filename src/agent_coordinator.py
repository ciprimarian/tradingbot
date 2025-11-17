# src/agents/agent_coordinator.py

from typing import List, Dict, Any, Optional
from enum import Enum
import pandas as pd
import numpy as np

from src.agents.base_agent import BaseAgent, AgentSignal, SignalType
from src.utils.logger import get_logger


class AggregationMethod(Enum):
    """Methods for aggregating multiple agent signals"""
    WEIGHTED_AVERAGE = "weighted_average"
    MAJORITY_VOTE = "majority_vote"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    UNANIMOUS = "unanimous"


class AgentCoordinator:
    """
    Coordinates multiple agents and aggregates their signals.
    """
    
    def __init__(
        self,
        agents: List[BaseAgent],
        aggregation_method: AggregationMethod = AggregationMethod.CONFIDENCE_WEIGHTED,
        min_confidence_threshold: float = 0.5,
        name: str = "AgentCoordinator"
    ):
        """
        """
        self.agents = agents
        self.aggregation_method = aggregation_method
        self.min_confidence_threshold = min_confidence_threshold
        self.name = name
        self.logger = get_logger(__name__)
        
        self._validate_agents()
        self.logger.info(
            f"Initialized {self.name} with {len(self.agents)} agents using {aggregation_method.value}"
        )
    
    def _validate_agents(self):
        """Validate that all agents are properly configured"""
        if not self.agents:
            raise ValueError("At least one agent must be provided")
        
        # Check for duplicate names
        names = [agent.name for agent in self.agents]
        if len(names) != len(set(names)):
            raise ValueError("Agent names must be unique")
    
    def get_signals(self, data: pd.DataFrame, **kwargs) -> Dict[str, AgentSignal]:
        """
        Get signals from all agents.
        """
        signals = {}
        for agent in self.agents:
            try:
                signal = agent.analyze(data, **kwargs)
                signals[agent.name] = signal
                self.logger.debug(
                    f"{agent.name}: {signal.signal_type.name} "
                    f"(confidence: {signal.confidence:.2f})"
                )
            except Exception as e:
                self.logger.error(f"Error getting signal from {agent.name}: {e}")
                # Create a neutral signal with zero confidence on error
                signals[agent.name] = AgentSignal(
                    signal_type=SignalType.NEUTRAL,
                    confidence=0.0,
                    reasoning=f"Error: {str(e)}"
                )
        
        return signals
    
    def aggregate_signals(
        self,
        signals: Dict[str, AgentSignal]
    ) -> AgentSignal:
        """
        Aggregate signals from all agents based on the selected method.
        """
        if self.aggregation_method == AggregationMethod.WEIGHTED_AVERAGE:
            return self._weighted_average(signals)
        elif self.aggregation_method == AggregationMethod.CONFIDENCE_WEIGHTED:
            return self._confidence_weighted(signals)
        elif self.aggregation_method == AggregationMethod.MAJORITY_VOTE:
            return self._majority_vote(signals)
        elif self.aggregation_method == AggregationMethod.UNANIMOUS:
            return self._unanimous(signals)
        else:
            raise ValueError(f"Unknown aggregation method: {self.aggregation_method}")
    
    def _weighted_average(self, signals: Dict[str, AgentSignal]) -> AgentSignal:
        """Aggregate using agent weights"""
        weighted_sum = 0.0
        total_weight = 0.0
        confidences = []
        
        for agent in self.agents:
            if agent.name in signals:
                signal = signals[agent.name]
                weighted_sum += signal.signal_type.value * agent.weight
                total_weight += agent.weight
                confidences.append(signal.confidence)
        
        if total_weight == 0:
            return AgentSignal(
                signal_type=SignalType.NEUTRAL,
                confidence=0.0,
                reasoning="No valid agents contributed to decision"
            )
        
        avg_signal = weighted_sum / total_weight
        avg_confidence = np.mean(confidences)
        
        return self._create_aggregated_signal(avg_signal, avg_confidence, signals)
    
    def _confidence_weighted(self, signals: Dict[str, AgentSignal]) -> AgentSignal:
        """Aggregate using both agent weights and signal confidence"""
        weighted_sum = 0.0
        total_weight = 0.0
        
        for agent in self.agents:
            if agent.name in signals:
                signal = signals[agent.name]
                # Weight by both agent weight and signal confidence
                effective_weight = agent.weight * signal.confidence
                weighted_sum += signal.signal_type.value * effective_weight
                total_weight += effective_weight
        
        if total_weight == 0:
            return AgentSignal(
                signal_type=SignalType.NEUTRAL,
                confidence=0.0,
                reasoning="No confident signals from agents"
            )
        
        avg_signal = weighted_sum / total_weight
        # Use normalized total weight as confidence
        max_possible_weight = sum(agent.weight for agent in self.agents)
        avg_confidence = min(total_weight / max_possible_weight, 1.0)
        
        return self._create_aggregated_signal(avg_signal, avg_confidence, signals)
    
    def _majority_vote(self, signals: Dict[str, AgentSignal]) -> AgentSignal:
        """Aggregate using simple majority voting"""
        votes = {
            SignalType.STRONG_BUY: 0,
            SignalType.BUY: 0,
            SignalType.NEUTRAL: 0,
            SignalType.SELL: 0,
            SignalType.STRONG_SELL: 0
        }
        confidences = []
        
        for signal in signals.values():
            votes[signal.signal_type] += 1
            confidences.append(signal.confidence)
        
        # Find majority
        max_votes = max(votes.values())
        majority_signal = [k for k, v in votes.items() if v == max_votes][0]
        
        # Confidence is average of all signals
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        # Reduce confidence if no clear majority
        total_votes = sum(votes.values())
        majority_ratio = max_votes / total_votes if total_votes > 0 else 0
        adjusted_confidence = avg_confidence * majority_ratio
        
        reasoning = f"Majority vote: {max_votes}/{total_votes} agents voted {majority_signal.name}"
        
        return AgentSignal(
            signal_type=majority_signal,
            confidence=adjusted_confidence,
            reasoning=reasoning,
            metadata={"votes": {k.name: v for k, v in votes.items()}}
        )
    
    def _unanimous(self, signals: Dict[str, AgentSignal]) -> AgentSignal:
        """Require unanimous agreement (or close to it)"""
        signal_types = [s.signal_type for s in signals.values()]
        confidences = [s.confidence for s in signals.values()]
        
        # Check if all signals agree
        unique_signals = set(signal_types)
        
        if len(unique_signals) == 1:
            # Perfect agreement
            return AgentSignal(
                signal_type=signal_types[0],
                confidence=np.mean(confidences),
                reasoning=f"Unanimous agreement: all {len(signals)} agents agree"
            )
        else:
            # No agreement - return neutral with low confidence
            return AgentSignal(
                signal_type=SignalType.NEUTRAL,
                confidence=0.3,
                reasoning=f"No consensus: {len(unique_signals)} different signals from agents"
            )
    
    def _create_aggregated_signal(
        self,
        avg_signal: float,
        confidence: float,
        signals: Dict[str, AgentSignal]
    ) -> AgentSignal:
        """Convert average signal value to SignalType"""
        # Map continuous value to discrete signal type
        if avg_signal >= 1.5:
            signal_type = SignalType.STRONG_BUY
        elif avg_signal >= 0.5:
            signal_type = SignalType.BUY
        elif avg_signal <= -1.5:
            signal_type = SignalType.STRONG_SELL
        elif avg_signal <= -0.5:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.NEUTRAL
        
        # Build reasoning
        agent_summaries = []
        for agent in self.agents:
            if agent.name in signals:
                sig = signals[agent.name]
                agent_summaries.append(
                    f"{agent.name}: {sig.signal_type.name} ({sig.confidence:.2f})"
                )
        
        reasoning = f"Aggregated from {len(signals)} agents. " + "; ".join(agent_summaries)
        
        return AgentSignal(
            signal_type=signal_type,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "aggregation_method": self.aggregation_method.value,
                "raw_signal_value": avg_signal,
                "agent_signals": {name: sig.to_dict() for name, sig in signals.items()}
            }
        )
    
    def decide(self, data: pd.DataFrame, **kwargs) -> Optional[AgentSignal]:
        """
        """
        # Collect signals from all agents
        signals = self.get_signals(data, **kwargs)
        
        # Aggregate signals
        final_signal = self.aggregate_signals(signals)
        
        self.logger.info(
            f"Final decision: {final_signal.signal_type.name} "
            f"(confidence: {final_signal.confidence:.2f})"
        )
        
        # Check if confidence meets threshold
        if final_signal.confidence < self.min_confidence_threshold:
            self.logger.warning(
                f"Signal confidence {final_signal.confidence:.2f} below threshold "
                f"{self.min_confidence_threshold:.2f} - returning None"
            )
            return None
        
        return final_signal
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about this coordinator"""
        return {
            "name": self.name,
            "num_agents": len(self.agents),
            "aggregation_method": self.aggregation_method.value,
            "min_confidence_threshold": self.min_confidence_threshold,
            "agents": [agent.get_info() for agent in self.agents]
        }
