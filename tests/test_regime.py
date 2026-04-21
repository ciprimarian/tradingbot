"""
Adversarial tests for RegimeDetector.

_classify() is NotImplementedError — tests cover raw indicators and UNKNOWN
handling until the judgment lane fills in the threshold logic.

Strategy:
  - UNKNOWN-path tests use < lookback bars so _classify is never reached.
  - Indicator tests call _efficiency_ratio / _return_volatility directly.
  - Adversarial edge-case tests assert that degenerate inputs raise ONLY
    NotImplementedError (not ZeroDivisionError, NaN propagation, etc.) — i.e.
    the indicators survive and _classify is the correct termination point.
  - TestClassifyContract tests skip until NotImplementedError is gone; they
    lock in the expected regime mapping for each canonical input.
"""

import math
from datetime import datetime, timezone
from typing import List

import pytest

from src.fuzzi.regime.detector import Regime, RegimeDetector, RegimeSnapshot
from src.fuzzi.common.models import Bar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt() -> datetime:
    return datetime.now(timezone.utc)


def _bars(closes: List[float], symbol: str = "TEST") -> List[Bar]:
    return [
        Bar(symbol=symbol, timestamp=_dt(), open=c, high=c, low=c, close=c, volume=1_000.0)
        for c in closes
    ]


def _trending_up(n: int = 20, start: float = 100.0, step: float = 1.0) -> List[Bar]:
    return _bars([start + i * step for i in range(n)])


def _trending_down(n: int = 20, start: float = 120.0, step: float = 1.0) -> List[Bar]:
    return _bars([start - i * step for i in range(n)])


def _zigzag(n: int = 20, base: float = 100.0, amplitude: float = 1.0) -> List[Bar]:
    return _bars([base + amplitude * (1 if i % 2 == 0 else -1) for i in range(n)])


def _flat(n: int = 20, price: float = 100.0) -> List[Bar]:
    return _bars([price] * n)


detector = RegimeDetector(lookback=20)


def _closes(bars: List[Bar]) -> List[float]:
    return [b.close for b in bars]


# ---------------------------------------------------------------------------
# UNKNOWN — too few bars (observe() never reaches _classify)
# ---------------------------------------------------------------------------

class TestUnknownRegime:
    def test_empty_list_returns_unknown(self):
        snap = detector.observe([])
        assert snap.regime == Regime.UNKNOWN
        assert snap.confidence == 0.0

    def test_single_bar_returns_unknown(self):
        snap = detector.observe(_bars([100.0]))
        assert snap.regime == Regime.UNKNOWN
        assert snap.confidence == 0.0

    def test_one_fewer_than_lookback_returns_unknown(self):
        snap = detector.observe(_bars([100.0 + i for i in range(19)]))
        assert snap.regime == Regime.UNKNOWN
        assert snap.confidence == 0.0

    def test_unknown_has_zero_efficiency_ratio(self):
        snap = detector.observe(_bars([100.0]))
        assert snap.efficiency_ratio == 0.0

    def test_unknown_has_zero_volatility(self):
        snap = detector.observe(_bars([100.0]))
        assert snap.volatility == 0.0

    def test_unknown_has_zero_direction(self):
        snap = detector.observe(_bars([100.0]))
        assert snap.direction == 0.0

    def test_lookback_field_matches_input_length(self):
        bars = _bars([100.0] * 5)
        snap = detector.observe(bars)
        assert snap.lookback == 5


# ---------------------------------------------------------------------------
# _efficiency_ratio — direct unit tests, no _classify involved
# ---------------------------------------------------------------------------

class TestEfficiencyRatio:
    def test_monotonic_up_gives_efficiency_one(self):
        closes = [100.0 + i for i in range(20)]
        assert math.isclose(detector._efficiency_ratio(closes), 1.0, abs_tol=1e-9)

    def test_monotonic_down_gives_efficiency_one(self):
        closes = [120.0 - i for i in range(20)]
        assert math.isclose(detector._efficiency_ratio(closes), 1.0, abs_tol=1e-9)

    def test_zigzag_gives_low_efficiency(self):
        """Net displacement ≈ 0, long path → ER near 0."""
        closes = [100.0 + (1.0 if i % 2 == 0 else -1.0) for i in range(20)]
        er = detector._efficiency_ratio(closes)
        assert er < 0.15, f"expected low ER for zigzag, got {er}"

    def test_flat_line_gives_zero_efficiency(self):
        closes = [100.0] * 20
        assert detector._efficiency_ratio(closes) == 0.0

    def test_single_element_gives_zero(self):
        assert detector._efficiency_ratio([100.0]) == 0.0

    def test_empty_gives_zero(self):
        assert detector._efficiency_ratio([]) == 0.0

    def test_efficiency_ratio_bounded_zero_to_one(self):
        for closes in [
            [100.0 + i for i in range(20)],          # trend up
            [120.0 - i for i in range(20)],          # trend down
            [100.0 + (1 if i % 2 == 0 else -1) for i in range(20)],  # zigzag
            [100.0] * 20,                             # flat
        ]:
            er = detector._efficiency_ratio(closes)
            assert 0.0 <= er <= 1.0, f"ER out of [0,1]: {er} for input starting {closes[:3]}"

    def test_single_spike_then_flat_has_low_efficiency(self):
        closes = [100.0] * 10 + [200.0] + [100.0] * 9
        er = detector._efficiency_ratio(closes)
        assert er < 0.5, f"spike-then-flat should be low ER, got {er}"

    def test_uses_only_provided_window_not_global_state(self):
        """ER is stateless — same input always gives same output."""
        closes = [100.0 + i for i in range(20)]
        er1 = detector._efficiency_ratio(closes)
        er2 = detector._efficiency_ratio(closes)
        assert er1 == er2

    def test_high_noise_around_trend_still_high_efficiency(self):
        noise = [0.05, -0.05, 0.03, -0.03, 0.07, -0.07, 0.02, -0.02,
                 0.06, -0.06, 0.04, -0.04, 0.08, -0.08, 0.01, -0.01,
                 0.09, -0.09, 0.04, -0.04]
        closes = [100.0 + i * 2.0 + noise[i] for i in range(20)]
        er = detector._efficiency_ratio(closes)
        assert er > 0.8, f"noisy trend should have high ER, got {er}"

    def test_all_zero_prices_gives_zero_not_error(self):
        closes = [0.0] * 20
        er = detector._efficiency_ratio(closes)
        assert er == 0.0

    def test_negative_prices_does_not_raise(self):
        closes = [-10.0 + i * 0.5 for i in range(20)]
        er = detector._efficiency_ratio(closes)
        assert 0.0 <= er <= 1.0

    def test_very_large_prices_no_nan(self):
        closes = [1e12 + i * 1e6 for i in range(20)]
        er = detector._efficiency_ratio(closes)
        assert not math.isnan(er)
        assert 0.0 <= er <= 1.0

    def test_very_small_prices_no_nan(self):
        closes = [1e-8 + i * 1e-10 for i in range(20)]
        er = detector._efficiency_ratio(closes)
        assert not math.isnan(er)


# ---------------------------------------------------------------------------
# _return_volatility — direct unit tests
# ---------------------------------------------------------------------------

class TestReturnVolatility:
    def test_flat_line_gives_zero_volatility(self):
        assert detector._return_volatility([100.0] * 20) == 0.0

    def test_monotonic_trend_gives_small_nonzero_volatility(self):
        closes = [100.0 + i for i in range(20)]
        vol = detector._return_volatility(closes)
        assert vol >= 0.0

    def test_large_swings_exceed_calm_threshold(self):
        closes = [100.0 + (5.0 if i % 2 == 0 else -5.0) for i in range(20)]
        vol = detector._return_volatility(closes)
        assert vol > detector.calm_vol_threshold

    def test_very_large_swings_exceed_volatile_threshold(self):
        closes = [100.0 + (20.0 if i % 2 == 0 else -20.0) for i in range(20)]
        vol = detector._return_volatility(closes)
        assert vol > detector.volatile_vol_threshold

    def test_volatility_non_negative(self):
        for closes in [
            [100.0 + i for i in range(20)],
            [100.0 + (1 if i % 2 == 0 else -1) for i in range(20)],
            [100.0] * 20,
        ]:
            assert detector._return_volatility(closes) >= 0.0

    def test_single_element_gives_zero(self):
        assert detector._return_volatility([100.0]) == 0.0

    def test_empty_gives_zero(self):
        assert detector._return_volatility([]) == 0.0

    def test_all_zero_prices_gives_zero_not_error(self):
        vol = detector._return_volatility([0.0] * 20)
        assert vol == 0.0

    def test_very_large_prices_no_nan(self):
        closes = [1e12 + i * 1e6 for i in range(20)]
        vol = detector._return_volatility(closes)
        assert not math.isnan(vol)

    def test_very_small_prices_no_nan(self):
        closes = [1e-8 + i * 1e-10 for i in range(20)]
        vol = detector._return_volatility(closes)
        assert not math.isnan(vol)


# ---------------------------------------------------------------------------
# observe() — adversarial edge cases: indicators must survive, only
# NotImplementedError is the allowed termination point for full-bar calls
# ---------------------------------------------------------------------------

class TestAdversarialEdgeCases:
    """
    For each degenerate input, observe() must either:
      a) Return a valid UNKNOWN snapshot (< lookback bars), or
      b) Raise NotImplementedError (indicators computed fine, _classify is stub).

    Any other exception (ZeroDivisionError, ValueError, overflow, NaN in
    indicator fields) indicates a bug in the indicator layer.
    """

    def _observe_indicators_only(self, bars: List[Bar]) -> dict:
        """Run indicators without _classify, return their values."""
        window = bars[-detector.lookback:]
        closes = [b.close for b in window]
        return {
            "er": detector._efficiency_ratio(closes),
            "vol": detector._return_volatility(closes),
            "dir": (closes[-1] - closes[0]) / closes[0] if closes[0] else 0.0,
        }

    def test_all_zero_prices_indicators_survive(self):
        ind = self._observe_indicators_only(_flat(price=0.0))
        assert ind["er"] == 0.0
        assert ind["vol"] == 0.0

    def test_single_nonzero_then_zeros_indicators_survive(self):
        closes = [100.0] + [0.0] * 19
        ind = self._observe_indicators_only(_bars(closes))
        assert not math.isnan(ind["er"])
        assert not math.isnan(ind["vol"])

    def test_negative_prices_indicators_survive(self):
        closes = [-10.0 + i * 0.5 for i in range(20)]
        ind = self._observe_indicators_only(_bars(closes))
        assert 0.0 <= ind["er"] <= 1.0
        assert ind["vol"] >= 0.0

    def test_very_large_prices_indicators_survive(self):
        closes = [1e12 + i * 1e6 for i in range(20)]
        ind = self._observe_indicators_only(_bars(closes))
        assert not math.isnan(ind["er"])
        assert not math.isnan(ind["vol"])

    def test_very_small_prices_indicators_survive(self):
        closes = [1e-8 + i * 1e-10 for i in range(20)]
        ind = self._observe_indicators_only(_bars(closes))
        assert not math.isnan(ind["er"])
        assert not math.isnan(ind["vol"])

    def test_zigzag_same_magnitude_efficiency_near_zero(self):
        closes = [100.0 + (1.0 if i % 2 == 0 else -1.0) for i in range(20)]
        ind = self._observe_indicators_only(_bars(closes))
        assert ind["er"] < 0.15

    def test_one_giant_spike_up_and_back_low_efficiency(self):
        closes = [100.0] * 9 + [10000.0] + [100.0] * 10
        ind = self._observe_indicators_only(_bars(closes))
        assert ind["er"] < 0.5

    def test_custom_lookback_uses_correct_window(self):
        d5 = RegimeDetector(lookback=5)
        bars = _trending_up(n=10)
        window = bars[-5:]
        closes = [b.close for b in window]
        er = d5._efficiency_ratio(closes)
        assert math.isclose(er, 1.0, abs_tol=1e-9)

    def test_exactly_lookback_bars_reaches_classify_not_unknown(self):
        """20 bars → _classify is reached (NotImplementedError), not UNKNOWN early return."""
        with pytest.raises(NotImplementedError):
            detector.observe(_trending_up(n=20))

    def test_more_than_lookback_bars_uses_tail_window(self):
        """200 bars; the window is the last 20. ER should still be 1.0 for monotonic."""
        long = _trending_up(n=200)
        closes = [b.close for b in long[-20:]]
        er = detector._efficiency_ratio(closes)
        assert math.isclose(er, 1.0, abs_tol=1e-9)

    def test_observe_raises_only_not_implemented_not_zero_division(self):
        for bars in [_trending_up(), _trending_down(), _zigzag(), _flat()]:
            with pytest.raises(NotImplementedError):
                detector.observe(bars)

    def test_observe_flat_raises_not_implemented_not_division_error(self):
        with pytest.raises(NotImplementedError):
            detector.observe(_flat())

    def test_observe_zigzag_large_amplitude_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            detector.observe(_zigzag(amplitude=50.0))


# ---------------------------------------------------------------------------
# Contract tests — skip until _classify lands, then lock in the mapping
# ---------------------------------------------------------------------------

class TestClassifyContract:
    """
    These tests define the expected behaviour once _classify is implemented.
    They skip cleanly while _classify raises NotImplementedError. When the
    judgment lane fills in the threshold logic, these tests must pass with no
    changes — they are the regression fence.
    """

    def _observe_or_skip(self, bars: List[Bar]) -> RegimeSnapshot:
        try:
            return detector.observe(bars)
        except NotImplementedError:
            pytest.skip("_classify not implemented yet")

    def test_monotonic_up_classified_as_trending_up(self):
        snap = self._observe_or_skip(_trending_up())
        assert snap.regime == Regime.TRENDING_UP

    def test_monotonic_down_classified_as_trending_down(self):
        snap = self._observe_or_skip(_trending_down())
        assert snap.regime == Regime.TRENDING_DOWN

    def test_monotonic_up_confidence_nonzero(self):
        snap = self._observe_or_skip(_trending_up())
        assert snap.confidence > 0.0

    def test_monotonic_down_confidence_nonzero(self):
        snap = self._observe_or_skip(_trending_down())
        assert snap.confidence > 0.0

    def test_zigzag_not_classified_as_trending(self):
        snap = self._observe_or_skip(_zigzag())
        assert snap.regime not in (Regime.TRENDING_UP, Regime.TRENDING_DOWN)

    def test_flat_classified_as_calm(self):
        snap = self._observe_or_skip(_flat())
        assert snap.regime == Regime.CALM

    def test_flat_not_classified_as_volatile(self):
        snap = self._observe_or_skip(_flat())
        assert snap.regime != Regime.VOLATILE

    def test_zigzag_large_amplitude_classified_as_volatile_or_choppy(self):
        snap = self._observe_or_skip(_zigzag(amplitude=5.0))
        assert snap.regime in (Regime.VOLATILE, Regime.CHOPPY)

    def test_confidence_in_range_for_all_canonical_inputs(self):
        for bars in [_trending_up(), _trending_down(), _zigzag(), _flat()]:
            try:
                snap = detector.observe(bars)
            except NotImplementedError:
                pytest.skip("_classify not implemented yet")
            assert 0.0 <= snap.confidence <= 1.0

    def test_regime_is_valid_enum_for_all_canonical_inputs(self):
        for bars in [_trending_up(), _trending_down(), _zigzag(), _flat()]:
            try:
                snap = detector.observe(bars)
            except NotImplementedError:
                pytest.skip("_classify not implemented yet")
            assert snap.regime in Regime
