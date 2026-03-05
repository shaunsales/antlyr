"""
ADX Trend Following Strategy

Enters long when ADX indicates a strong uptrend, short when strong downtrend.
Uses 1m bars for execution/TSL and 1h bars for trend indicators.

This is an example single-asset strategy demonstrating the multi-interval
data_spec() pattern.
"""

from typing import Optional

from core.strategy.base import SingleAssetStrategy, StrategyConfig
from core.strategy.data import StrategyDataSpec, StrategyData
from core.strategy.position import Signal, Position


class ADXTrend(SingleAssetStrategy):
    """
    ADX-based trend following on Binance BTCUSDT Futures.

    Entry logic (checked every 1m bar using 1h indicators):
    - Long when ADX > threshold and price > SMA
    - Short when ADX > threshold and price < SMA

    Exit logic:
    - Close when ADX drops below threshold (trend weakening)
    - Close when price crosses SMA against position direction
    """

    def __init__(
        self,
        adx_threshold: float = 25.0,
        sma_length: int = 50,
        config: Optional[StrategyConfig] = None,
    ):
        config = config or StrategyConfig(name="ADXTrend")
        super().__init__(config)
        self.adx_threshold = adx_threshold
        self.sma_length = sma_length

    def data_spec(self) -> StrategyDataSpec:
        return StrategyDataSpec(
            venue="binance",
            market="futures",
            ticker="BTCUSDT",
            intervals={
                "1m": [],
                "1h": [
                    ("adx", {"length": 14}),
                    ("sma", {"length": self.sma_length}),
                ],
            },
        )

    def required_indicators(self) -> list[tuple[str, dict]]:
        # Legacy — not used when running via data_spec() path
        return [
            ("adx", {"length": 14}),
            ("sma", {"length": self.sma_length}),
        ]

    def on_bar(self, idx, data, capital, position):
        # Placeholder — will be refactored to use StrategyData in 3B.2
        return Signal.hold()
