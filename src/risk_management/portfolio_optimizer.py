# src/risk_management/portfolio_optimizer.py

"""
Portfolio Optimization using gradient descent and numerical optimization
Demonstrates Optimization branch of AI
Not perfectly polished but shows understanding of optimization concepts
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.optimize import minimize
import pandas as pd

from src.utils.common_imports import get_logger


class PortfolioOptimizer:
    """
    Optimizes portfolio allocation using numerical optimization techniques
    
    Demonstrates Optimization branch:
    - Objective function definition (Sharpe ratio, returns, risk)
    - Constraint handling (weights sum to 1, no short selling)
    - Gradient descent and other optimization algorithms
    - Parameter tuning and convergence
    
    Uses scipy.optimize but could implement gradient descent manually
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.logger = get_logger(__name__)
        
    def optimize_weights(
        self, 
        returns: pd.DataFrame,
        method: str = 'sharpe',
        allow_short: bool = False
    ) -> Dict[str, float]:
        """
        Find optimal portfolio weights
        
        Args:
            returns: DataFrame with returns for each asset (columns are assets)
            method: 'sharpe', 'min_variance', or 'max_return'
            allow_short: Whether to allow short positions (negative weights)
            
        Returns:
            Dictionary mapping asset names to optimal weights
        """
        if returns.empty:
            self.logger.warning("No returns data provided")
            return {}
        
        n_assets = len(returns.columns)
        
        # Initial guess: equal weights
        initial_weights = np.ones(n_assets) / n_assets
        
        # Define constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # weights sum to 1
        ]
        
        # Define bounds
        if allow_short:
            bounds = tuple((-1, 1) for _ in range(n_assets))  # can go short
        else:
            bounds = tuple((0, 1) for _ in range(n_assets))  # long only
        
        # Choose objective function
        if method == 'sharpe':
            objective = lambda w: -self._sharpe_ratio(w, returns)  # negative because we minimize
        elif method == 'min_variance':
            objective = lambda w: self._portfolio_variance(w, returns)
        elif method == 'max_return':
            objective = lambda w: -self._portfolio_return(w, returns)  # negative to minimize
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Run optimization
        # Using SLSQP (Sequential Least Squares Programming) - good for constrained optimization
        self.logger.info(f"Running portfolio optimization (method={method})...")
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        if not result.success:
            self.logger.warning(f"Optimization did not converge: {result.message}")
        
        # Extract optimal weights
        optimal_weights = result.x
        
        # Create result dictionary
        weight_dict = {
            asset: float(w) for asset, w in zip(returns.columns, optimal_weights)
        }
        
        # Log results
        self.logger.info("Optimal portfolio weights:")
        for asset, weight in weight_dict.items():
            self.logger.info(f"  {asset}: {weight:.4f}")
        
        # Calculate metrics for optimal portfolio
        opt_return = self._portfolio_return(optimal_weights, returns)
        opt_vol = np.sqrt(self._portfolio_variance(optimal_weights, returns))
        opt_sharpe = self._sharpe_ratio(optimal_weights, returns)
        
        self.logger.info(f"Expected return: {opt_return*100:.2f}%")
        self.logger.info(f"Volatility: {opt_vol*100:.2f}%")
        self.logger.info(f"Sharpe ratio: {opt_sharpe:.3f}")
        
        return weight_dict
    
    def _portfolio_return(self, weights: np.ndarray, returns: pd.DataFrame) -> float:
        """Calculate expected portfolio return"""
        mean_returns = returns.mean()
        return np.dot(weights, mean_returns) * 252  # annualized
    
    def _portfolio_variance(self, weights: np.ndarray, returns: pd.DataFrame) -> float:
        """Calculate portfolio variance"""
        cov_matrix = returns.cov() * 252  # annualized
        return np.dot(weights, np.dot(cov_matrix, weights))
    
    def _sharpe_ratio(self, weights: np.ndarray, returns: pd.DataFrame) -> float:
        """
        Calculate Sharpe ratio - risk-adjusted return
        Higher is better
        """
        port_return = self._portfolio_return(weights, returns)
        port_vol = np.sqrt(self._portfolio_variance(weights, returns))
        
        if port_vol == 0:
            return 0.0
        
        return (port_return - self.risk_free_rate) / port_vol
    
    def optimize_position_size(
        self,
        expected_return: float,
        volatility: float,
        current_capital: float,
        risk_tolerance: float = 0.02
    ) -> float:
        """
        Optimize position size using Kelly Criterion (simplified)
        
        This is a simple optimization problem:
        Maximize E[log(wealth)] subject to risk constraints
        
        Args:
            expected_return: Expected return of the trade
            volatility: Volatility/risk of the asset
            current_capital: Current portfolio value
            risk_tolerance: Max % of capital to risk (default 2%)
            
        Returns:
            Optimal position size in dollars
        """
        if volatility == 0 or expected_return <= 0:
            return 0.0
        
        # Kelly criterion: f* = (expected_return) / (variance)
        # Simplified version for continuous returns
        kelly_fraction = expected_return / (volatility ** 2)
        
        # Apply safety factor - Kelly can be aggressive
        # Using half-Kelly is common (more conservative)
        safe_kelly = kelly_fraction * 0.5
        
        # Cap at risk tolerance
        final_fraction = min(safe_kelly, risk_tolerance)
        final_fraction = max(0, final_fraction)  # no negative positions
        
        position_size = current_capital * final_fraction
        
        self.logger.debug(f"Kelly fraction: {kelly_fraction:.4f}")
        self.logger.debug(f"Safe Kelly (0.5x): {safe_kelly:.4f}")
        self.logger.debug(f"Final fraction: {final_fraction:.4f}")
        self.logger.debug(f"Position size: ${position_size:.2f}")
        
        return position_size


class GradientDescentOptimizer:
    """
    Simple gradient descent optimizer - implemented from scratch
    to show understanding of optimization fundamentals
    
    Less efficient than scipy but demonstrates the concepts
    """
    
    def __init__(self, learning_rate: float = 0.01, max_iterations: int = 1000):
        self.learning_rate = learning_rate
        self.max_iterations = max_iterations
        self.logger = get_logger(__name__)
        
    def optimize(
        self,
        objective_func,
        gradient_func,
        initial_params: np.ndarray,
        tolerance: float = 1e-6
    ) -> Tuple[np.ndarray, List[float]]:
        """
        Minimize objective function using gradient descent
        
        Args:
            objective_func: Function to minimize f(params)
            gradient_func: Gradient of objective function df/dparams
            initial_params: Starting point
            tolerance: Convergence threshold
            
        Returns:
            (optimal_params, history of objective values)
        """
        params = initial_params.copy()
        history = []
        
        for iteration in range(self.max_iterations):
            # Evaluate objective
            obj_value = objective_func(params)
            history.append(obj_value)
            
            # Calculate gradient
            grad = gradient_func(params)
            
            # Check convergence
            grad_norm = np.linalg.norm(grad)
            if grad_norm < tolerance:
                self.logger.info(f"Converged in {iteration} iterations")
                break
            
            # Update parameters using gradient descent
            # params = params - learning_rate * gradient
            params = params - self.learning_rate * grad
            
            # Log progress every 100 iterations
            if iteration % 100 == 0:
                self.logger.debug(f"Iteration {iteration}: obj={obj_value:.6f}, ||grad||={grad_norm:.6f}")
        
        self.logger.info(f"Final objective value: {history[-1]:.6f}")
        return params, history
    
    def optimize_with_momentum(
        self,
        objective_func,
        gradient_func,
        initial_params: np.ndarray,
        momentum: float = 0.9,
        tolerance: float = 1e-6
    ) -> Tuple[np.ndarray, List[float]]:
        """
        Gradient descent with momentum - converges faster
        Momentum helps escape local minima and speeds up convergence
        """
        params = initial_params.copy()
        velocity = np.zeros_like(params)
        history = []
        
        for iteration in range(self.max_iterations):
            obj_value = objective_func(params)
            history.append(obj_value)
            
            grad = gradient_func(params)
            
            if np.linalg.norm(grad) < tolerance:
                self.logger.info(f"Converged with momentum in {iteration} iterations")
                break
            
            # Update velocity with momentum
            velocity = momentum * velocity - self.learning_rate * grad
            
            # Update parameters
            params = params + velocity
            
            if iteration % 100 == 0:
                self.logger.debug(f"Iteration {iteration}: obj={obj_value:.6f}")
        
        return params, history
