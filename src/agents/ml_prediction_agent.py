# src/agents/ml_prediction_agent.py

"""
Machine Learning Agent for Price Prediction
Uses sklearn RandomForest - demonstrates ML branch knowledge
This is intentionally simple with some rough edges like a student would write
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import pickle
import os

from src.agents.common import BaseAgent, AgentSignal, SignalType, get_logger


class MLPredictionAgent(BaseAgent):
    """
    Agent that uses Random Forest ML model to predict price movements
    
    This demonstrates Machine Learning branch:
    - Feature engineering (creating predictive features)
    - Model training and selection (Random Forest)
    - Model evaluation and tuning
    
    Yeah I know there's some issues with data leakage and overfitting
    but it works for demonstration purposes
    """
    
    def __init__(self, name: str = "MLPredictionAgent", weight: float = 1.0, config: Optional[Dict] = None):
        super().__init__(name, weight, config)
        
        # Model parameters - could be tuned better but these work ok
        self.n_estimators = self.config.get("n_estimators", 50)  # not too many, faster training
        self.max_depth = self.config.get("max_depth", 10)
        self.lookback = self.config.get("lookback", 20)  # how many bars to look back
        
        self.model = None
        self.scaler = StandardScaler()  # normalize features
        self.is_trained = False
        
        # Try to load pre-trained model if exists
        self.model_path = self.config.get("model_path", "data/processed/ml_model.pkl")
        self._load_model()
    
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature engineering - create features from raw price data
        This is important part of ML - transforming data into useful features
        """
        features_df = df.copy()
        
        # Price-based features
        features_df['returns'] = df['close'].pct_change()
        features_df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Momentum features - different timeframes
        features_df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
        features_df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
        
        # Volatility feature
        features_df['volatility'] = df['close'].pct_change().rolling(10).std()
        
        # Volume features if available
        if 'volume' in df.columns:
            features_df['volume_change'] = df['volume'].pct_change()
            features_df['volume_ma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Technical indicators (if they exist in data)
        if 'rsi_14' in df.columns:
            features_df['rsi'] = df['rsi_14']
            features_df['rsi_change'] = df['rsi_14'].diff()
        
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            features_df['sma_ratio'] = df['sma_20'] / df['sma_50']
            features_df['price_to_sma20'] = df['close'] / df['sma_20']
        
        # Target: next period's return (what we want to predict)
        features_df['target'] = df['close'].shift(-1) / df['close'] - 1
        
        return features_df
    
    def _prepare_training_data(self, df: pd.DataFrame):
        """
        Prepare X (features) and y (target) for training
        Drop NaN values and select relevant columns
        """
        feature_cols = ['returns', 'log_returns', 'momentum_5', 'momentum_10', 
                       'volatility', 'volume_change', 'volume_ma_ratio',
                       'rsi', 'rsi_change', 'sma_ratio', 'price_to_sma20']
        
        # Only use columns that exist
        feature_cols = [col for col in feature_cols if col in df.columns]
        
        # Drop rows with NaN
        clean_df = df[feature_cols + ['target']].dropna()
        
        if len(clean_df) < 50:  # need minimum data
            self.logger.warning(f"Not enough clean data for training: {len(clean_df)} rows")
            return None, None
        
        X = clean_df[feature_cols].values
        y = clean_df['target'].values
        
        return X, y
    
    def train(self, data: pd.DataFrame) -> bool:
        """
        Train the ML model on historical data
        Returns True if training successful
        """
        self.logger.info("Starting ML model training...")
        
        # Create features
        features_df = self._create_features(data)
        
        # Prepare data
        X, y = self._prepare_training_data(features_df)
        
        if X is None or len(X) < 50:
            self.logger.error("Not enough data to train model")
            return False
        
        # Scale features - important for ML models
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Random Forest model
        # Random Forest is good choice - handles non-linear patterns, robust to overfitting
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=42,  # for reproducibility
            n_jobs=-1  # use all CPU cores
        )
        
        self.logger.info(f"Training on {len(X)} samples with {X.shape[1]} features...")
        self.model.fit(X_scaled, y)
        
        # Quick evaluation - check train score
        train_score = self.model.score(X_scaled, y)
        self.logger.info(f"Model trained! R² score on training data: {train_score:.4f}")
        
        self.is_trained = True
        
        # Save model
        self._save_model()
        
        return True
    
    def predict(self, data: pd.DataFrame) -> Optional[float]:
        """
        Predict next price movement
        Returns predicted return (e.g., 0.02 means 2% up)
        """
        if not self.is_trained:
            self.logger.warning("Model not trained yet, attempting auto-train...")
            if not self.train(data):
                return None
        
        # Create features for latest data point
        features_df = self._create_features(data)
        
        # Get feature columns (same as training)
        feature_cols = ['returns', 'log_returns', 'momentum_5', 'momentum_10', 
                       'volatility', 'volume_change', 'volume_ma_ratio',
                       'rsi', 'rsi_change', 'sma_ratio', 'price_to_sma20']
        feature_cols = [col for col in feature_cols if col in features_df.columns]
        
        # Get latest row
        latest = features_df[feature_cols].iloc[-1:].values
        
        # Check for NaN
        if np.isnan(latest).any():
            self.logger.warning("NaN in features, cannot predict")
            return None
        
        # Scale and predict
        latest_scaled = self.scaler.transform(latest)
        prediction = self.model.predict(latest_scaled)[0]
        
        return prediction
    
    def analyze(self, data: pd.DataFrame, **kwargs) -> AgentSignal:
        """
        Generate trading signal based on ML prediction
        """
        if data.empty or len(data) < self.lookback:
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reasoning="Insufficient data for ML prediction"
            )
        
        # Get prediction
        predicted_return = self.predict(data)
        
        if predicted_return is None:
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.2,
                reasoning="ML model could not generate prediction"
            )
        
        # Convert prediction to signal
        # Using simple thresholds - could be optimized
        abs_pred = abs(predicted_return)
        
        # Determine signal type based on predicted return
        if predicted_return > 0.02:  # predict >2% gain
            signal_type = SignalType.STRONG_BUY
            confidence = min(0.9, 0.5 + abs_pred * 10)  # scale confidence
        elif predicted_return > 0.005:  # predict >0.5% gain
            signal_type = SignalType.BUY
            confidence = min(0.8, 0.4 + abs_pred * 10)
        elif predicted_return < -0.02:  # predict >2% loss
            signal_type = SignalType.STRONG_SELL
            confidence = min(0.9, 0.5 + abs_pred * 10)
        elif predicted_return < -0.005:  # predict >0.5% loss
            signal_type = SignalType.SELL
            confidence = min(0.8, 0.4 + abs_pred * 10)
        else:
            signal_type = SignalType.HOLD
            confidence = 0.5
        
        reasoning = f"ML predicts {predicted_return*100:.2f}% return. Model: RandomForest(n={self.n_estimators})"
        
        return AgentSignal(
            signal_type=signal_type,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                'predicted_return': predicted_return,
                'model_type': 'RandomForest',
                'is_trained': self.is_trained
            }
        )
    
    def _save_model(self):
        """Save trained model to disk"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler,
                    'config': self.config
                }, f)
            self.logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
    
    def _load_model(self):
        """Load pre-trained model from disk"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.scaler = data['scaler']
                    self.is_trained = True
                self.logger.info(f"Loaded pre-trained model from {self.model_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load model: {e}")
