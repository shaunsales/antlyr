# Single Asset Strategy Plan

End-to-end workflow for backtesting single-asset strategies on Binance Futures perp data.

Three stages: **Data → Backtest → Visualisation**

---

## Design Principles

### No Look-Ahead Bias
- Backtest iterates on **1m bars** for precise execution.
- Larger-interval data (1h, etc.) is accessed via the **last fully closed bar** only.
- At T=14:32, the latest usable 1h bar is the one that closed at 14:00, not the in-progress 14:00–15:00 bar.
- Enforced by the `StrategyData` accessor, not by the strategy author.

### Strategy Structure
```
strategies/                            # Strategy Python classes
  adx_trend.py                         # ADXTrend (example SingleAsset)
  basis_arb.py                         # BasisArbitrage
  _example_strategies.py               # More examples

output/strategies/{strategy_name}/     # Generated data + results
  manifest.json                        # Config, intervals, indicators, date range
  data/
    1m.parquet                         # OHLCV (execution interval)
    1h.parquet                         # OHLCV + indicators
  results/
    {run_id}_bars.parquet              # Bar-level state (nav, drawdown, position)
    {run_id}_trades.parquet            # Trade log with decision context
    {run_id}_meta.json                 # Run config + summary metrics
    {run_id}_tearsheet.html            # QuantStats HTML tearsheet
```

### Metrics
All metrics computed via `quantstats.stats`:
- Sharpe, Sortino, Calmar ratios
- Max drawdown, win rate, profit factor
- Full HTML tearsheet via `quantstats.reports.html()`

---

## Phase 1: Strategy Data Builder ✅

Build the multi-interval data files that a strategy needs.

### 1.1 Strategy Data Interface ✅
Each strategy declares data dependencies via `data_spec()`:
```python
class ADXTrend(SingleAssetStrategy):
    def data_spec(self) -> StrategyDataSpec:
        return StrategyDataSpec(
            venue="binance", market="futures", ticker="BTCUSDT",
            intervals={"1m": [], "1h": [("adx", {"length": 14}), ("sma", {"length": 50})]},
        )
```
- `intervals` maps each interval to `(indicator, params)` tuples.
- `1m` always required (execution interval).
- Date range chosen in the UI, stored in manifest.

### 1.2 Data Builder ✅
- Downloads OHLCV per interval from Binance.
- Computes indicators via `core/indicators/`.
- Validates coverage, gaps, bar counts.
- Saves each interval as parquet + `manifest.json`.

### 1.3 Web UI ✅
Strategy page at `/strategies/single-asset`:
- Strategy list sidebar (auto-discovers classes)
- Spec display (venue, ticker, intervals, indicators)
- Calendar month grid picker for date range (with warmup indication)
- Build/delete controls, data preview (chart + table)

---

## Phase 2: Backtest Engine ✅

Run the strategy on 1m bars with multi-interval data access.

### 2.1 Multi-Interval Data Accessor ✅
```python
class StrategyData:
    def bar(self, interval: str, timestamp) -> pd.Series:
        """Return the last FULLY CLOSED bar at or before timestamp."""
    def bars(self, interval: str, timestamp, n: int) -> pd.DataFrame:
        """Return last N fully closed bars."""
```
- Look-ahead-safe: `bar("1h", T)` returns bar whose `open_time + 1h <= T`.
- O(log n) lookups via searchsorted.

### 2.2 Strategy Interface ✅
```python
class SingleAssetStrategy(ABC):
    def on_bar(self, timestamp, data: StrategyData,
               balance: float, position: Optional[Position]) -> Signal:
        """Called every 1m bar."""
```
- Receives `StrategyData` (not raw DataFrame).
- Strategy queries whichever intervals it needs.

### 2.3 Decision Context Capture ✅
On every entry/exit, `data.snapshot(timestamp)` captures indicator values across all intervals. Stored in `trade.metadata` as `entry_context` + `exit_context`. Exported as JSON column in trades parquet.

### 2.4 Bar-Level State Recording ✅
Every 1m bar records: timestamp, close, balance, nav, drawdown_pct, position_side/size/pnl/pnl_pct, signal. Saved as `{run_id}_bars.parquet`.

### 2.5 Metrics & Output ✅
- QuantStats metrics from equity series.
- HTML tearsheet, bars parquet, trades parquet, meta JSON.

### 2.6 Parameter Optimisation (Deferred)
Grid search over named parameters. Deferred until single-run workflow is fully proven.

---

## Phase 3: Visualisation

React frontend for backtest results and strategy data.

### 3.1 Backtest Viewer ✅ (partial)
Backtest page at `/backtest`:
- **Run list sidebar** — select previous backtest runs
- **Metrics cards** — total return, Sharpe, drawdown, win rate, trades, profit factor
- **Price chart** — with trade entry/exit markers (green ↑ long, red ↓ short, purple ● exit)
- **Equity curve** — NAV over time
- **Drawdown chart** — drawdown % from peak
- **Trades table** — side, entry/exit times + prices, PnL, bars held, reasons
- **Tearsheet link** — opens QuantStats HTML in new tab
- All charts synced on time scale

### 3.2 Source Data Viewer ✅
Strategy page inline preview:
- Price + overlay indicators + indicator panels + volume (synced)
- Paginated data table

### 3.3 Run Backtest UI
- Select strategy, set starting capital + cost model params
- Click Run → show progress → auto-navigate to results
- Backend: `POST /backtest/run` (already exists)

### 3.4 Trade Inspector
- Click trade row → expand or side panel showing decision context
- Entry + exit indicator snapshots from `trade.metadata`

### 3.5 Optimisation Results (Deferred)
- Sortable results table for parameter sweep runs
- Click row → navigate to full backtest view

---

## Implementation Status

| Step | Deliverable | Status |
|------|-------------|--------|
| **Phase 1** | **Strategy Data Builder** | **✅ Done** |
| 1.1 | `StrategyDataSpec` + manifest schema | ✅ Done |
| 1.2 | Data builder (download, indicators, parquets) | ✅ Done |
| 1.3 | Strategy page UI (spec, build, preview) | ✅ Done |
| **Phase 2** | **Backtest Engine** | **✅ Done** |
| 2.1 | `StrategyData` multi-interval accessor | ✅ Done |
| 2.2 | Strategy interface + engine loop | ✅ Done |
| 2.3 | Decision context capture | ✅ Done |
| 2.4 | Bar-level state recording | ✅ Done |
| 2.5 | QuantStats metrics + output files | ✅ Done |
| 2.6 | Parameter optimisation | Deferred |
| **Frontend** | **React SPA** | **✅ Done** |
|  | Sidebar nav, pages, charts, tables, dark mode | ✅ Done |
|  | MonthRangePicker, OHLCV resampling, download page | ✅ Done |
| **Phase 3** | **Visualisation** | **✅ Done** |
| 3.1 | Backtest viewer (metrics, charts, trades, tearsheet) | ✅ Done |
| 3.2 | Source data viewer (chart + table preview) | ✅ Done |
| 3.3 | Run Backtest UI | ✅ Done |
| 3.4 | Trade inspector (decision context panel) | ✅ Done |
| 3.5 | Optimisation results table | Deferred |
