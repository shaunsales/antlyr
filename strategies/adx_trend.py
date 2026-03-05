"""
ADX Trend Following Strategy

Enters long when ADX indicates a strong uptrend, short when strong downtrend.
Uses 1m bars for execution/TSL and 1h bars for trend indicators.

This is an example single-asset strategy demonstrating the multi-interval
data_spec() pattern.
"""

from typing import Optional

import pandas as pd

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

    def on_bar(self, timestamp, data: StrategyData, balance: float, position: Optional[Position]):
        """
        V2 on_bar: called every 1m with multi-interval StrategyData.
        
        Uses 1h ADX + SMA for trend direction, 1m close for execution.
        """
        # Get latest closed 1h bar
        try:
            h1 = data.bar("1h", timestamp)
        except (ValueError, KeyError):
            return Signal.hold()  # No 1h data yet
        
        adx = h1.get("ADX_14")
        sma = h1.get(f"SMA_{self.sma_length}")
        
        # Need valid indicators
        if adx is None or sma is None or pd.isna(adx) or pd.isna(sma):
            return Signal.hold()
        
        # Current 1m close price
        m1 = data.bar("1m", timestamp)
        price = m1["close"]
        
        # --- Entry logic ---
        if position is None:
            if adx > self.adx_threshold and price > sma:
                return Signal.buy(
                    size=1.0,
                    reason=f"adx={adx:.1f}>thr price={price:.0f}>sma={sma:.0f}",
                )
            elif adx > self.adx_threshold and price < sma:
                return Signal.sell(
                    size=1.0,
                    reason=f"adx={adx:.1f}>thr price={price:.0f}<sma={sma:.0f}",
                )
        
        # --- Exit logic ---
        if position is not None:
            # Exit if trend weakens
            if adx < self.adx_threshold * 0.8:
                return Signal.close(reason=f"adx_weak={adx:.1f}")
            
            # Exit if price crosses SMA against position
            if position.side.value == "long" and price < sma:
                return Signal.close(reason=f"price={price:.0f}<sma={sma:.0f}")
            elif position.side.value == "short" and price > sma:
                return Signal.close(reason=f"price={price:.0f}>sma={sma:.0f}")
        
        return Signal.hold()
