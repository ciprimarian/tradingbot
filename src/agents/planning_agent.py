# src/agents/planning_agent.py

"""
Planning Agent using A* search algorithm
Demonstrates AI Planning branch - finding optimal sequence of actions
A bit messy but that's how learning looks like :)
"""

import heapq
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass
import pandas as pd
import numpy as np

from src.agents.common import BaseAgent, AgentSignal, SignalType, get_logger


@dataclass
class TradingState:
    """Represents a state in our planning problem"""
    position: int  # 0=cash, 1=long, -1=short (keeping simple)
    capital: float
    num_trades: int  # track transaction costs
    timestamp: int  # which bar we're at
    
    def __hash__(self):
        return hash((self.position, self.num_trades, self.timestamp))
    
    def __eq__(self, other):
        return (self.position == other.position and 
                self.timestamp == other.timestamp)


@dataclass 
class Action:
    """Possible trading actions"""
    name: str  # "BUY", "SELL", "HOLD"
    cost: float = 0.0  # transaction cost


class TradingPlannerAgent(BaseAgent):
    """
    Uses A* search to plan optimal trading sequence
    
    Demonstrates Planning branch:
    - State space definition (trading states)
    - Goal-based planning (maximize profit)
    - Heuristic search (A* algorithm)
    - Action selection and sequencing
    
    Simplified version - in reality would be more complex
    but shows I understand the concepts
    """
    
    def __init__(self, name: str = "PlannerAgent", weight: float = 1.0, config: Optional[Dict] = None):
        super().__init__(name, weight, config)
        
        # Initialize logger
        self.logger = get_logger(self.__class__.__name__)
        
        # Planning parameters
        self.lookahead = self.config.get("lookahead", 5)  # how far to plan ahead
        self.transaction_cost = self.config.get("transaction_cost", 0.001)  # 0.1%
        self.max_iterations = self.config.get("max_iterations", 100)
        
        self.logger.info(f"Planning agent initialized with lookahead={self.lookahead}")
    
    def _get_possible_actions(self, state: TradingState) -> List[Action]:
        """
        Get available actions from current state
        This defines our action space
        """
        actions = []
        
        # Always can HOLD
        actions.append(Action("HOLD", cost=0.0))
        
        # Can BUY if not already long
        if state.position <= 0:
            actions.append(Action("BUY", cost=self.transaction_cost))
        
        # Can SELL if currently long
        if state.position > 0:
            actions.append(Action("SELL", cost=self.transaction_cost))
        
        return actions
    
    def _apply_action(self, state: TradingState, action: Action, price_change: float) -> TradingState:
        """
        Apply an action to a state and get new state
        This is our transition function
        """
        new_position = state.position
        new_capital = state.capital
        new_trades = state.num_trades
        
        if action.name == "BUY":
            new_position = 1
            new_capital = state.capital * (1 - action.cost)  # pay transaction cost
            new_trades += 1
        elif action.name == "SELL":
            new_position = 0
            new_capital = state.capital * (1 - action.cost)
            new_trades += 1
        # HOLD doesn't change position
        
        # Apply market movement to capital based on position
        if new_position == 1:  # long position gains/loses with market
            new_capital = new_capital * (1 + price_change)
        
        return TradingState(
            position=new_position,
            capital=new_capital,
            num_trades=new_trades,
            timestamp=state.timestamp + 1
        )
    
    def _heuristic(self, state: TradingState, goal_timestamp: int, avg_return: float) -> float:
        """
        Heuristic function for A* - estimates cost to goal
        Lower is better
        
        Estimates potential remaining profit based on average returns
        This guides the search towards profitable paths
        """
        remaining_steps = goal_timestamp - state.timestamp
        if remaining_steps <= 0:
            return 0.0
        
        # Optimistic estimate: assume we capture average returns
        potential_gain = state.capital * (avg_return * remaining_steps)
        
        # Return negative (want to maximize gain, but A* minimizes cost)
        return -potential_gain
    
    def _a_star_search(
        self, 
        initial_state: TradingState, 
        price_data: pd.DataFrame
    ) -> Tuple[List[str], float]:
        """
        A* search algorithm to find optimal trading plan
        
        Returns: (list of actions, expected final value)
        """
        # Priority queue: (priority, state, path, cost)
        # priority = g(n) + h(n) where g=cost so far, h=heuristic
        frontier = []
        start_priority = self._heuristic(initial_state, len(price_data)-1, 0.001)
        heapq.heappush(frontier, (start_priority, 0, initial_state, []))
        
        explored: Set[TradingState] = set()
        iterations = 0
        best_plan = []
        best_value = initial_state.capital
        
        # Calculate average return for heuristic
        returns = price_data['close'].pct_change().fillna(0)
        avg_return = returns.mean()
        
        while frontier and iterations < self.max_iterations:
            iterations += 1
            
            _, cost_so_far, current_state, path = heapq.heappop(frontier)
            
            # Check if we've explored this state
            if current_state in explored:
                continue
            explored.add(current_state)
            
            # Check if reached end of data (goal)
            if current_state.timestamp >= len(price_data) - 1:
                if current_state.capital > best_value:
                    best_value = current_state.capital
                    best_plan = path
                continue
            
            # Get next price change
            if current_state.timestamp + 1 < len(price_data):
                next_return = returns.iloc[current_state.timestamp + 1]
            else:
                next_return = 0.0
            
            # Expand possible actions
            for action in self._get_possible_actions(current_state):
                new_state = self._apply_action(current_state, action, next_return)
                
                if new_state not in explored:
                    new_path = path + [action.name]
                    new_cost = cost_so_far - new_state.capital  # negative = gain
                    
                    # Calculate priority with heuristic
                    h_value = self._heuristic(new_state, len(price_data)-1, avg_return)
                    priority = new_cost + h_value
                    
                    heapq.heappush(frontier, (priority, new_cost, new_state, new_path))
        
        self.logger.debug(f"A* search completed in {iterations} iterations")
        self.logger.debug(f"Best plan value: {best_value:.2f} vs initial: {initial_state.capital:.2f}")
        
        return best_plan, best_value
    
    def analyze(self, data: pd.DataFrame, **kwargs) -> AgentSignal:
        """
        Use planning to determine next action
        Runs A* to find optimal sequence, then takes first action
        """
        if data.empty or len(data) < self.lookahead + 1:
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reasoning="Not enough data for planning"
            )
        
        # Get current position from kwargs if available
        current_position = kwargs.get('current_position', 0)  # 0=cash, 1=long
        
        # Define initial state
        initial_capital = 10000.0  # doesn't matter much, just for planning
        initial_state = TradingState(
            position=current_position,
            capital=initial_capital,
            num_trades=0,
            timestamp=len(data) - self.lookahead - 1
        )
        
        # Get recent data for planning
        planning_data = data.tail(self.lookahead + 1).copy()
        
        # Run A* search
        try:
            plan, final_value = self._a_star_search(initial_state, planning_data)
        except Exception as e:
            self.logger.error(f"Planning search failed: {e}")
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.3,
                reasoning=f"Planning failed: {str(e)}"
            )
        
        # Extract first action from plan
        if not plan:
            next_action = "HOLD"
            confidence = 0.4
        else:
            next_action = plan[0]
            # Confidence based on expected profit
            expected_return = (final_value - initial_capital) / initial_capital
            confidence = min(0.9, 0.5 + abs(expected_return) * 2)
        
        # Convert to signal type
        signal_map = {
            "BUY": SignalType.BUY,
            "SELL": SignalType.SELL,
            "HOLD": SignalType.HOLD
        }
        signal_type = signal_map.get(next_action, SignalType.HOLD)
        
        reasoning = (f"A* planning suggests {next_action}. "
                    f"Plan: {' -> '.join(plan[:3])}{'...' if len(plan) > 3 else ''}")
        
        return AgentSignal(
            signal_type=signal_type,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                'full_plan': plan,
                'expected_return': (final_value - initial_capital) / initial_capital,
                'plan_length': len(plan)
            }
        )
