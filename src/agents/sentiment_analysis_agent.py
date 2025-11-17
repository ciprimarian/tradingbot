# src/agents/sentiment_analysis_agent.py

import pandas as pd
import numpy as np

from typing import Any, Dict, Optional
from src.agents.base_agent import BaseAgent, AgentSignal, SignalType
from src.utils.logger import get_logger

class SimpleSentimentAgent(BaseAgent):
   
    '''Agent that analyzes sentiment from news, social media and text data'''

    def __init__(self, name: str = "SimpleSentimentAgent", weight: float = 1.0, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, weight, config)
        self.logger = get_logger(__name__)

        # Configuration
        self.use_ml_model = self.config.get("use_ml_model", False)
        self.model_name = self.config.get("model_name", "default-sentiment-model")
   

        #load model if needed
        self.model = None
        self.tokenizer = None

        if self.use_ml_model:
            self._load_sentiment_model()

    def _load_sentiment_model(self):
        '''Load pre-trained sentiment analysis model'''
        try:
            from transformers import pipeline
            self.logger.info(f"Loading sentiment model: {self.model_name}")
            self.model = pipeline("sentiment-analysis", model=self.model_name, device=-1) # Use CPU (change to 0 for GPU)
            self.logger.info("Sentiment model loaded successfully.")
        except ImportError:
            self.logger.warning(
                'transformers library not installed. '
                'install with pip install transformers torch'
            )
            self.use_ml_model = False
        except Exception as e:
            self.logger.error(f"Error loading sentiment model: {e}")
            self.use_ml_model = False

    def analyze(self, data, **kwargs) -> AgentSignal:
        # Placeholder implementation
        if len(data) < 5:
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.5,
                reasoning="Simple sentiment analysis placeholder."
            )
    
        recent = data.tail(10)
        returns = recent['close'].pct_change().dropna()

        positive_days = (returns > 0).sum()
        total_days = len(returns)
        positive_ratio = positive_days / total_days if total_days > 0 else 0

        avg_return = returns.mean()

        if positive_ratio > 0.7 and avg_return > 0:
            return AgentSignal(
                signal_type=SignalType.BUY,
                confidence=0.7,
                reasoning=f"Bullish sentiment detected: {positive_ratio:.0%} up days."
            )
        else:
            return AgentSignal(
                signal_type=SignalType.HOLD,
                confidence=0.5,
                reasoning="Mixed sentiment"
            )
        
    def _analyze_text_sentiment(self, texts: list[str]) -> tuple[float, float]:
        '''Analyze sentiment from list of texts'''
        if not texts or not self.model:
            return 0.0, 0.0, 'Text: N/A'
        
        try:
            #limit to most recent texts to avoid rate limits
            text_to_analyze = texts[-20:]
            truncated_texts = [text[:512] for text in text_to_analyze]
            results = self.model(truncated_texts)

            sentiment_scores = []
            for res in results:
                label = res['label'].lower()
                score = res['score']
                if label == 'positive':
                    sentiment_scores.append((1.0, score))
                elif label == 'negative':
                    sentiment_scores.append((-1.0, score))
                else:
                    sentiment_scores.append((0.0, score * 0.5)) # neutral

            average_sentiment = np.mean(sentiment_scores)
            confidence = abs(average_sentiment) 
            signal_value = average_sentiment * 2

            if average_sentiment > 0.3:
                desc = "Positive"
            elif average_sentiment < -0.3:
                desc = "Negative"
            else:
                desc = "Neutral"
            
            return(signal_value, confidence, f"Text Sentiment: {desc} sentiment ({average_sentiment:.2f}, {len(texts)} items)")
        
        except Exception as e:
            self.logger.error(f"Error analyzing text sentiment: {e}")
            return 0.0, 0.0, f"Text Sentiment: Error ({str(e)[:30]})"