"""
Backtest routes.

Handles listing, viewing, and running backtests.
Reads results from output/strategies/{name}/results/.
"""

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.routes.strategy import discover_strategies, _get_strategy_instance
from core.strategy.data import strategy_folder, STRATEGIES_OUTPUT_DIR
from core.strategy.engine import BacktestEngine
from core.strategy.position import CostModel, DEFAULT_COSTS

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _list_runs() -> list[dict]:
    """Scan all strategy folders for backtest runs."""
    runs = []
    if not STRATEGIES_OUTPUT_DIR.exists():
        return runs

    for strat_dir in sorted(STRATEGIES_OUTPUT_DIR.iterdir()):
        results_dir = strat_dir / "results"
        if not results_dir.is_dir():
            continue

        for meta_file in sorted(results_dir.glob("*_meta.json"), reverse=True):
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                run_id = meta.get("run_id", meta_file.stem.replace("_meta", ""))
                runs.append({
                    "strategy_name": strat_dir.name,
                    "run_id": run_id,
                    "meta": meta,
                    "folder": str(results_dir),
                })
            except Exception:
                continue

    return runs


def _downsample_series(timestamps, values, max_points=2000):
    """Downsample a time series for chart display."""
    if len(timestamps) <= max_points:
        return [
            {"time": int(t.timestamp()) if hasattr(t, "timestamp") else int(pd.Timestamp(t).timestamp()), "value": round(float(v), 4)}
            for t, v in zip(timestamps, values)
            if not (isinstance(v, float) and np.isnan(v))
        ]

    step = max(1, len(timestamps) // max_points)
    return [
        {"time": int(timestamps[i].timestamp()) if hasattr(timestamps[i], "timestamp") else int(pd.Timestamp(timestamps[i]).timestamp()), "value": round(float(values[i]), 4)}
        for i in range(0, len(timestamps), step)
        if not (isinstance(values[i], float) and np.isnan(values[i]))
    ]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
async def backtest_page():
    """List all backtest runs and strategies."""
    runs = _list_runs()
    strategies = discover_strategies()
    return {"runs": runs, "strategies": strategies}


@router.get("/view/{strategy_name}/{run_id}")
async def view_run(strategy_name: str, run_id: str):
    """Load and display a backtest run — returns JSON."""
    results_dir = strategy_folder(strategy_name) / "results"

    meta_path = results_dir / f"{run_id}_meta.json"
    if not meta_path.exists():
        return {"error": "Run not found"}

    with open(meta_path) as f:
        meta = json.load(f)

    # Load bar-level data for charts
    bars_path = results_dir / f"{run_id}_bars.parquet"
    chart_data = {}
    if bars_path.exists():
        bars_df = pd.read_parquet(bars_path)
        ts = bars_df.index
        chart_data["price"] = _downsample_series(ts, bars_df["close"])
        chart_data["equity"] = _downsample_series(ts, bars_df["nav"])
        chart_data["drawdown"] = _downsample_series(ts, bars_df["drawdown_pct"])

    # Load trades
    trades = []
    trades_path = results_dir / f"{run_id}_trades.parquet"
    if trades_path.exists():
        trades_df = pd.read_parquet(trades_path)
        for _, row in trades_df.iterrows():
            # Parse metadata (decision context) if available
            raw_meta = row.get("metadata", None)
            trade_metadata = None
            if raw_meta is not None:
                if isinstance(raw_meta, str):
                    try:
                        trade_metadata = json.loads(raw_meta)
                    except (json.JSONDecodeError, TypeError):
                        pass
                elif isinstance(raw_meta, dict):
                    trade_metadata = raw_meta

            trades.append({
                "side": row.get("side", ""),
                "entry_time": str(row["entry_time"]),
                "entry_price": round(float(row["entry_price"]), 2),
                "exit_time": str(row["exit_time"]),
                "exit_price": round(float(row["exit_price"]), 2),
                "size": round(float(row["size"]), 0),
                "gross_pnl": round(float(row["gross_pnl"]), 2),
                "costs": round(float(row["costs"]), 2),
                "net_pnl": round(float(row["net_pnl"]), 2),
                "bars_held": int(row["bars_held"]),
                "entry_reason": row.get("entry_reason", ""),
                "exit_reason": row.get("exit_reason", ""),
                "metadata": trade_metadata,
            })

        # Build trade markers for chart
        chart_data["markers"] = []
        for _, row in trades_df.iterrows():
            entry_ts = pd.Timestamp(row["entry_time"])
            exit_ts = pd.Timestamp(row["exit_time"])
            is_long = row.get("side", "") == "long"
            chart_data["markers"].append({
                "time": int(entry_ts.timestamp()),
                "position": "belowBar" if is_long else "aboveBar",
                "color": "#22c55e" if is_long else "#ef4444",
                "shape": "arrowUp" if is_long else "arrowDown",
                "text": f"{'L' if is_long else 'S'} {row.get('entry_reason', '')}",
            })
            chart_data["markers"].append({
                "time": int(exit_ts.timestamp()),
                "position": "aboveBar" if is_long else "belowBar",
                "color": "#a855f7",
                "shape": "circle",
                "text": f"X {row.get('exit_reason', '')}",
            })

    # Tearsheet link
    tearsheet_exists = (results_dir / f"{run_id}_tearsheet.html").exists()

    return {
        "strategy_name": strategy_name,
        "run_id": run_id,
        "meta": meta,
        "chart_data": chart_data,
        "trades": trades,
        "tearsheet_exists": tearsheet_exists,
    }


@router.get("/tearsheet/{strategy_name}/{run_id}")
async def serve_tearsheet(strategy_name: str, run_id: str):
    """Serve the QuantStats HTML tearsheet."""
    path = strategy_folder(strategy_name) / "results" / f"{run_id}_tearsheet.html"
    if not path.exists():
        return JSONResponse({"error": "Tearsheet not found"}, status_code=404)
    return FileResponse(path, media_type="text/html")


class RunBacktestRequest(BaseModel):
    class_name: str
    capital: float = 100_000
    commission_bps: float = 3.5
    slippage_bps: float = 2.0
    funding_daily_bps: float = 5.0


@router.post("/run")
async def run_backtest(req: RunBacktestRequest):
    """Run a backtest for a strategy."""
    instance = _get_strategy_instance(req.class_name)
    if instance is None:
        return {"success": False, "error": "Strategy not found"}

    spec = instance.data_spec()
    if spec is None:
        return {"success": False, "error": "Strategy does not define data_spec()"}

    try:
        costs = CostModel(
            commission_bps=req.commission_bps,
            slippage_bps=req.slippage_bps,
            funding_daily_bps=req.funding_daily_bps,
        )
        engine = BacktestEngine(verbose=False)
        result = engine.run(instance, capital=req.capital, costs=costs)

        return {
            "success": True,
            "strategy_name": instance.name,
            "run_id": result.config.get("run_id", ""),
            "metrics": result.summary(),
            "total_trades": len(result.trades),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
