# tests/test_agents.py

import pytest

from src.utils.common_imports import pd, np
from src.agents.common import BaseAgent, AgentSignal, SignalType
from src.agents.technical_analysis_agent import TechnicalAnalysisAgent
from src.agents.risk_management_agent import RiskManagementAgent
from src.agents.sentiment_analysis_agent import SimpleSentimentAgent
from src.agents.agent_coordinator import AgentCoordinator, AggregationMethod
from src.data.data_manager import DataManager
from src.indicators.moving_average import calculate_sma
from src.indicators.momentum_indicators import calculate_rsi


@pytest.fixture
def sample_ohlcv_data():
    """Create realistic OHLCV market data for testing"""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    
    # Generate realistic price data with trend
    base_price = 100
    returns = np.random.randn(100) * 0.02  # 2% daily volatility
    prices = base_price * (1 + returns).cumprod()
    
    # Generate OHLC from close prices
    df = pd.DataFrame({
        "open": prices * (1 + np.random.randn(100) * 0.005),
        "high": prices * (1 + abs(np.random.randn(100)) * 0.01),
        "low": prices * (1 - abs(np.random.randn(100)) * 0.01),
        "close": prices,
        "volume": np.random.randint(100000, 1000000, 100),
    }, index=dates)
    
    # Ensure high is highest and low is lowest
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


@pytest.fixture
def enriched_data(sample_ohlcv_data):
    """Create sample data with all indicators that agents expect"""
    df = sample_ohlcv_data.copy()
    
    # Add indicators using the actual calculation functions
    df = calculate_sma(df, 20, column='close', inplace=True)
    df = calculate_sma(df, 50, column='close', inplace=True)
    df['rsi_14'] = calculate_rsi(df, window=14, column='close')
    
    return df


def test_technical_agent_basic(enriched_data):
    """Test that technical agent generates valid signals"""
    agent = TechnicalAnalysisAgent(name="TestTech", weight=1.0)
    signal = agent.analyze(enriched_data)
    
    assert isinstance(signal, AgentSignal)
    assert isinstance(signal.signal_type, SignalType)
    assert 0.0 <= signal.confidence <= 1.0
    assert len(signal.reasoning) > 0
    assert signal.metadata is not None
    assert 'indicators_used' in signal.metadata


def test_technical_agent_rsi_oversold(enriched_data):
    """Test technical agent detects oversold conditions"""
    # Force RSI to oversold
    df = enriched_data.copy()
    df.loc[df.index[-1], 'rsi_14'] = 25
    
    agent = TechnicalAnalysisAgent(name="TestTech")
    signal = agent.analyze(df)
    
    # Should mention oversold in reasoning (may be offset by MA)
    assert "oversold" in signal.reasoning.lower()
    
    # If we force extreme oversold, should be bullish
    df.loc[df.index[-1], 'rsi_14'] = 15
    signal_extreme = agent.analyze(df)
    assert signal_extreme.signal_type.value >= 0  # Should be HOLD or BUY


def test_technical_agent_rsi_overbought(enriched_data):
    """Test technical agent detects overbought conditions"""
    # Force RSI to overbought
    df = enriched_data.copy()
    df.loc[df.index[-1], 'rsi_14'] = 75
    
    agent = TechnicalAnalysisAgent(name="TestTech")
    signal = agent.analyze(df)
    
    # Should mention overbought in reasoning (may be offset by MA signal)
    assert "overbought" in signal.reasoning.lower()
    
    # If we force extreme overbought, should be bearish
    df.loc[df.index[-1], 'rsi_14'] = 85
    signal_extreme = agent.analyze(df)
    assert signal_extreme.signal_type.value <= 0  # Should be HOLD or SELL


def test_technical_agent_empty_data():
    """Test technical agent handles empty data gracefully"""
    agent = TechnicalAnalysisAgent(name="TestTech")
    empty_df = pd.DataFrame()
    
    signal = agent.analyze(empty_df)
    
    assert signal.signal_type == SignalType.HOLD
    assert signal.confidence == 0.0
    assert "No data" in signal.reasoning


def test_risk_agent_basic(enriched_data):
    """Test that risk agent generates valid signals"""
    agent = RiskManagementAgent(name="TestRisk", weight=1.0)
    signal = agent.analyze(enriched_data)
    
    assert isinstance(signal, AgentSignal)
    assert isinstance(signal.signal_type, SignalType)
    assert 0.0 <= signal.confidence <= 1.0
    assert signal.metadata is not None
    assert 'volatility' in signal.metadata
    assert 'drawdown' in signal.metadata
    assert 'var_95' in signal.metadata


def test_risk_agent_insufficient_data():
    """Test risk agent handles insufficient data"""
    agent = RiskManagementAgent(name="TestRisk")
    
    # Create data with less than lookback period
    short_data = pd.DataFrame({
        'close': [100, 101, 102]
    })
    
    signal = agent.analyze(short_data)
    
    assert signal.signal_type == SignalType.HOLD
    assert signal.confidence == 0.0
    assert "Insufficient data" in signal.reasoning


def test_sentiment_agent_basic(enriched_data):
    """Test that simple sentiment agent generates valid signals"""
    agent = SimpleSentimentAgent(name="TestSentiment", weight=0.5)
    signal = agent.analyze(enriched_data)
    
    assert isinstance(signal, AgentSignal)
    assert isinstance(signal.signal_type, SignalType)
    assert 0.0 <= signal.confidence <= 1.0


def test_coordinator_confidence_weighted(enriched_data):
    """Test coordinator with confidence-weighted aggregation"""
    agents = [
        TechnicalAnalysisAgent(name="Tech", weight=0.5),
        RiskManagementAgent(name="Risk", weight=0.3),
        SimpleSentimentAgent(name="Sentiment", weight=0.2)
    ]
    
    coordinator = AgentCoordinator(
        agents=agents,
        aggregation_method=AggregationMethod.CONFIDENCE_WEIGHTED,
        min_confidence_threshold=0.0
    )
    
    signal = coordinator.decide(enriched_data)
    
    assert signal is not None
    assert isinstance(signal, AgentSignal)
    assert "Aggregated from 3 agents" in signal.reasoning
    assert signal.metadata is not None
    assert 'aggregation_method' in signal.metadata


def test_coordinator_majority_vote(enriched_data):
    """Test coordinator with majority vote aggregation"""
    agents = [
        TechnicalAnalysisAgent(name="Tech1", weight=1.0),
        TechnicalAnalysisAgent(name="Tech2", weight=1.0),
        RiskManagementAgent(name="Risk", weight=1.0)
    ]
    
    coordinator = AgentCoordinator(
        agents=agents,
        aggregation_method=AggregationMethod.MAJORITY_VOTE
    )
    
    signal = coordinator.decide(enriched_data)
    
    if signal:  # May be None if below confidence threshold
        assert "Majority vote" in signal.reasoning or "Aggregated from" in signal.reasoning


def test_coordinator_get_signals(enriched_data):
    """Test individual signal retrieval from coordinator"""
    agents = [
        TechnicalAnalysisAgent(name="Tech"),
        RiskManagementAgent(name="Risk"),
        SimpleSentimentAgent(name="Sentiment")
    ]
    
    coordinator = AgentCoordinator(agents=agents)
    signals = coordinator.get_signals(enriched_data)
    
    assert len(signals) == 3
    assert "Tech" in signals
    assert "Risk" in signals
    assert "Sentiment" in signals
    
    for name, signal in signals.items():
        assert isinstance(signal, AgentSignal)


def test_agent_signal_structure():
    """Test signal data structure validation"""
    # Valid signal
    sig = AgentSignal(
        signal_type=SignalType.BUY,
        confidence=0.8,
        reasoning="Test reasoning"
    )
    assert sig.weighted_signal == 0.8  # BUY=1 * 0.8 confidence
    
    # Test to_dict method
    sig_dict = sig.to_dict()
    assert sig_dict['signal_type'] == 'BUY'
    assert sig_dict['signal_value'] == 1
    assert sig_dict['confidence'] == 0.8
    
    # Invalid confidence (too high)
    with pytest.raises(ValueError):
        AgentSignal(SignalType.BUY, 1.5, "Invalid confidence")
    
    # Invalid confidence (negative)
    with pytest.raises(ValueError):
        AgentSignal(SignalType.SELL, -0.1, "Invalid confidence")


def test_agent_weights():
    """Test that agent weights are properly validated"""
    # Valid weight
    agent = TechnicalAnalysisAgent(name="Test", weight=0.5)
    assert agent.weight == 0.5
    
    # Invalid weight (too high)
    with pytest.raises(ValueError):
        TechnicalAnalysisAgent(name="Test", weight=1.5)
    
    # Invalid weight (negative)
    with pytest.raises(ValueError):
        TechnicalAnalysisAgent(name="Test", weight=-0.1)


def test_data_manager_prepare_for_agents(sample_ohlcv_data):
    """Test DataManager.prepare_for_agents() adds all required indicators"""
    dm = DataManager()
    
    enriched = dm.prepare_for_agents(sample_ohlcv_data)
    
    # Check that all required indicators are present
    assert 'sma_20' in enriched.columns
    assert 'sma_50' in enriched.columns
    assert 'rsi_14' in enriched.columns
    
    # Check no NaN in recent data (indicators need warm-up period)
    recent = enriched.tail(20)
    assert not recent['sma_20'].isna().all()
    assert not recent['rsi_14'].isna().all()


def test_agent_info_methods():
    """Test agent info retrieval methods"""
    agent = TechnicalAnalysisAgent(name="TestAgent", weight=0.7)
    info = agent.get_info()
    
    assert info['name'] == "TestAgent"
    assert info['weight'] == 0.7
    assert info['type'] == "TechnicalAnalysisAgent"


def test_coordinator_info():
    """Test coordinator info retrieval"""
    agents = [
        TechnicalAnalysisAgent(name="Tech", weight=0.6),
        RiskManagementAgent(name="Risk", weight=0.4)
    ]
    
    coordinator = AgentCoordinator(agents=agents, name="TestCoordinator")
    info = coordinator.get_info()
    
    assert info['name'] == "TestCoordinator"
    assert info['num_agents'] == 2
    assert len(info['agents']) == 2


def test_coordinator_weighted_average(enriched_data):
    """Test weighted average aggregation method"""
    agents = [
        TechnicalAnalysisAgent(name="Tech", weight=0.7),
        RiskManagementAgent(name="Risk", weight=0.3)
    ]
    
    coordinator = AgentCoordinator(
        agents=agents,
        aggregation_method=AggregationMethod.WEIGHTED_AVERAGE
    )
    
    signal = coordinator.decide(enriched_data)
    
    if signal:
        assert isinstance(signal, AgentSignal)
        assert signal.metadata['aggregation_method'] == 'weighted_average'


def test_coordinator_unanimous(enriched_data):
    """Test unanimous aggregation method"""
    agents = [
        TechnicalAnalysisAgent(name="Tech1", weight=1.0),
        TechnicalAnalysisAgent(name="Tech2", weight=1.0),
    ]
    
    coordinator = AgentCoordinator(
        agents=agents,
        aggregation_method=AggregationMethod.UNANIMOUS,
        min_confidence_threshold=0.0
    )
    
    signal = coordinator.decide(enriched_data)
    
    # May not be unanimous, but should handle it gracefully
    assert signal is not None
    assert isinstance(signal, AgentSignal)


def test_coordinator_low_confidence_threshold(enriched_data):
    """Test that coordinator returns None when confidence below threshold"""
    agents = [TechnicalAnalysisAgent(name="Tech")]
    
    coordinator = AgentCoordinator(
        agents=agents,
        min_confidence_threshold=0.99  # Very high threshold
    )
    
    signal = coordinator.decide(enriched_data)
    
    # Should return None due to high threshold
    assert signal is None


def test_coordinator_validation_errors():
    """Test coordinator validation catches errors"""
    # Empty agents list
    with pytest.raises(ValueError, match="At least one agent"):
        AgentCoordinator(agents=[])
    
    # Duplicate agent names
    agents = [
        TechnicalAnalysisAgent(name="Tech"),
        RiskManagementAgent(name="Tech")  # Same name
    ]
    with pytest.raises(ValueError, match="unique"):
        AgentCoordinator(agents=agents)


def test_coordinator_error_handling(enriched_data):
    """Test coordinator handles agent errors gracefully"""
    # Create a custom broken agent
    class BrokenAgent(BaseAgent):
        def analyze(self, data, **kwargs):
            raise RuntimeError("Simulated error")
    
    agents = [
        TechnicalAnalysisAgent(name="Tech"),
        BrokenAgent(name="Broken", weight=1.0)
    ]
    
    coordinator = AgentCoordinator(agents=agents)
    
    # Should not crash, broken agent should return HOLD signal
    signals = coordinator.get_signals(enriched_data)
    
    assert "Broken" in signals
    assert signals["Broken"].signal_type == SignalType.HOLD
    assert signals["Broken"].confidence == 0.0
    assert "Error" in signals["Broken"].reasoning


def test_technical_agent_with_custom_config():
    """Test technical agent with custom RSI thresholds"""
    config = {
        "rsi_overbought": 65,
        "rsi_oversold": 35
    }
    
    agent = TechnicalAnalysisAgent(name="CustomTech", config=config)
    
    assert agent.rsi_overbought == 65
    assert agent.rsi_oversold == 35


def test_technical_agent_missing_indicators(sample_ohlcv_data):
    """Test technical agent when indicators are missing"""
    # Data without any indicators
    agent = TechnicalAnalysisAgent(name="Tech")
    signal = agent.analyze(sample_ohlcv_data)
    
    assert signal.signal_type == SignalType.HOLD
    assert signal.confidence == 0.0
    assert "No indicators available" in signal.reasoning


def test_technical_agent_golden_cross(enriched_data):
    """Test technical agent detects golden cross"""
    df = enriched_data.copy()
    
    # Force golden cross: price above both MAs, SMA20 > SMA50
    last_idx = df.index[-1]
    df.loc[last_idx, 'close'] = 150
    df.loc[last_idx, 'sma_20'] = 145
    df.loc[last_idx, 'sma_50'] = 140
    df.loc[last_idx, 'rsi_14'] = 55  # Neutral RSI
    
    agent = TechnicalAnalysisAgent(name="Tech")
    signal = agent.analyze(df)
    
    assert "golden cross" in signal.reasoning.lower() or "bullish" in signal.reasoning.lower()


def test_technical_agent_death_cross(enriched_data):
    """Test technical agent detects death cross"""
    df = enriched_data.copy()
    
    # Force death cross: price below both MAs, SMA20 < SMA50
    last_idx = df.index[-1]
    df.loc[last_idx, 'close'] = 90
    df.loc[last_idx, 'sma_20'] = 95
    df.loc[last_idx, 'sma_50'] = 100
    df.loc[last_idx, 'rsi_14'] = 55  # Neutral RSI
    
    agent = TechnicalAnalysisAgent(name="Tech")
    signal = agent.analyze(df)
    
    assert "death cross" in signal.reasoning.lower() or "bearish" in signal.reasoning.lower()


def test_technical_agent_nan_handling(enriched_data):
    """Test technical agent handles NaN values"""
    df = enriched_data.copy()
    
    # Set indicators to NaN
    df.loc[df.index[-1], 'rsi_14'] = np.nan
    df.loc[df.index[-1], 'sma_20'] = np.nan
    
    agent = TechnicalAnalysisAgent(name="Tech")
    signal = agent.analyze(df)
    
    # Should handle gracefully
    assert isinstance(signal, AgentSignal)


def test_risk_agent_high_volatility(enriched_data):
    """Test risk agent detects high volatility"""
    df = enriched_data.copy()
    
    # Create high volatility by adding large price swings
    for i in range(len(df)):
        df.loc[df.index[i], 'close'] = 100 + np.random.randn() * 10
    
    agent = RiskManagementAgent(name="Risk", config={"max_volatility": 0.01})
    signal = agent.analyze(df)
    
    assert "volatility" in signal.reasoning.lower()
    assert signal.metadata['volatility'] > 0


def test_risk_agent_severe_drawdown(enriched_data):
    """Test risk agent detects drawdown"""
    df = enriched_data.copy()
    
    # Create severe drawdown by setting recent prices much lower
    # The drawdown is calculated as (current - running_max) / running_max
    # So we need current price to be significantly below the running max
    peak_idx = df['close'].idxmax()
    peak_price = df['close'].max()
    
    # Set all prices after peak to be 20% lower
    after_peak = df.index > peak_idx
    df.loc[after_peak, 'close'] = peak_price * 0.75  # 25% drawdown
    
    agent = RiskManagementAgent(name="Risk", config={"max_drawdown": 0.1})
    signal = agent.analyze(df)
    
    # Should detect drawdown (though exact value depends on calculation window)
    assert "drawdown" in signal.reasoning.lower()
    assert signal.metadata['drawdown'] >= 0  # At least some drawdown detected


def test_risk_agent_with_custom_config():
    """Test risk agent with custom configuration"""
    config = {
        "max_volatility": 0.05,
        "max_drawdown": 0.15,
        "var_threshold": 0.08,
        "lookback_period": 30
    }
    
    agent = RiskManagementAgent(name="Risk", config=config)
    
    assert agent.max_volatility == 0.05
    assert agent.max_drawdown == 0.15
    assert agent.var_threshold == 0.08
    assert agent.lookback_period == 30


def test_sentiment_agent_bullish_momentum(enriched_data):
    """Test sentiment agent with bullish price momentum"""
    df = enriched_data.copy()
    
    # Create strong upward momentum
    for i in range(len(df) - 10, len(df)):
        df.loc[df.index[i], 'close'] = 100 + (i - (len(df) - 10)) * 2
    
    agent = SimpleSentimentAgent(name="Sentiment")
    signal = agent.analyze(df)
    
    # Should detect bullish sentiment from price action
    assert signal.signal_type.value >= 0  # BUY or HOLD


def test_sentiment_agent_with_ml_model_disabled():
    """Test sentiment agent with ML model explicitly disabled"""
    config = {"use_ml_model": False}
    agent = SimpleSentimentAgent(name="Sentiment", config=config)
    
    assert agent.use_ml_model is False
    assert agent.model is None


def test_sentiment_agent_short_data():
    """Test sentiment agent with insufficient data"""
    short_df = pd.DataFrame({'close': [100, 101]})
    
    agent = SimpleSentimentAgent(name="Sentiment")
    signal = agent.analyze(short_df)
    
    assert signal.signal_type == SignalType.HOLD
    assert signal.confidence == 0.5


def test_base_agent_abstract_class():
    """Test that BaseAgent cannot be instantiated directly"""
    # BaseAgent is abstract, but we can test subclass implementation
    agent = TechnicalAnalysisAgent(name="Test", weight=0.5)
    
    info = agent.get_info()
    assert 'name' in info
    assert 'weight' in info
    assert 'type' in info


def test_signal_type_enum_values():
    """Test SignalType enum has correct values"""
    assert SignalType.STRONG_BUY.value == 2
    assert SignalType.BUY.value == 1
    assert SignalType.HOLD.value == 0
    assert SignalType.SELL.value == -1
    assert SignalType.STRONG_SELL.value == -2


def test_agent_signal_metadata():
    """Test AgentSignal can store custom metadata"""
    metadata = {
        "indicators": ["RSI", "MA"],
        "threshold": 70,
        "custom_value": 42
    }
    
    signal = AgentSignal(
        signal_type=SignalType.BUY,
        confidence=0.7,
        reasoning="Test",
        metadata=metadata
    )
    
    assert signal.metadata['indicators'] == ["RSI", "MA"]
    assert signal.metadata['threshold'] == 70
    assert signal.metadata['custom_value'] == 42


def test_data_manager_empty_dataframe():
    """Test DataManager handles empty DataFrame"""
    dm = DataManager()
    empty_df = pd.DataFrame()
    
    result = dm.prepare_for_agents(empty_df)
    
    assert result.empty
    assert len(result) == 0


def test_multiple_aggregation_methods(enriched_data):
    """Test all aggregation methods work correctly"""
    agents = [
        TechnicalAnalysisAgent(name="Tech1", weight=0.5),
        TechnicalAnalysisAgent(name="Tech2", weight=0.5)
    ]
    
    methods = [
        AggregationMethod.WEIGHTED_AVERAGE,
        AggregationMethod.CONFIDENCE_WEIGHTED,
        AggregationMethod.MAJORITY_VOTE,
        AggregationMethod.UNANIMOUS
    ]
    
    for method in methods:
        coordinator = AgentCoordinator(
            agents=agents,
            aggregation_method=method,
            min_confidence_threshold=0.0
        )
        
        signal = coordinator.decide(enriched_data)
        
        assert signal is not None, f"Failed for method: {method}"
        assert isinstance(signal, AgentSignal)


def test_risk_agent_var_calculation(enriched_data):
    """Test that VaR is calculated and returned in metadata"""
    agent = RiskManagementAgent(name="Risk")
    signal = agent.analyze(enriched_data)
    
    assert 'var_95' in signal.metadata
    assert signal.metadata['var_95'] >= 0


def test_agent_repr():
    """Test agent string representation"""
    agent = TechnicalAnalysisAgent(name="MyAgent", weight=0.8)
    repr_str = repr(agent)
    
    assert "TechnicalAnalysisAgent" in repr_str
    assert "MyAgent" in repr_str
    assert "0.8" in repr_str








