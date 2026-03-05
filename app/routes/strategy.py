"""
Strategy Data Builder Routes

Web UI for discovering strategies, building data files, and managing strategy folders.
"""

import importlib
import inspect
import json
import pkgutil
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.strategy.base import SingleAssetStrategy
from core.data.storage import list_available_periods
from core.strategy.data import (
    StrategyDataSpec,
    StrategyDataBuilder,
    StrategyDataValidator,
    strategy_folder,
    load_manifest,
    _subtract_months,
)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


# ---------------------------------------------------------------------------
# Strategy auto-discovery
# ---------------------------------------------------------------------------

def discover_strategies() -> list[dict]:
    """
    Scan the strategies/ directory and find all SingleAssetStrategy subclasses
    that implement data_spec(). Returns a list of dicts with strategy metadata.
    """
    import strategies  # top-level strategies package

    results = []

    for importer, modname, ispkg in pkgutil.iter_modules(strategies.__path__):
        # Skip test/internal modules
        if modname.startswith("_"):
            continue

        try:
            module = importlib.import_module(f"strategies.{modname}")
        except Exception:
            continue

        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (
                inspect.isclass(obj)
                and issubclass(obj, SingleAssetStrategy)
                and obj is not SingleAssetStrategy
                and not attr_name.startswith("_")
            ):
                # Try to instantiate and get data_spec
                try:
                    instance = obj()
                    spec = instance.data_spec()
                except Exception:
                    spec = None

                results.append({
                    "class_name": attr_name,
                    "module": f"strategies.{modname}",
                    "name": instance.name if 'instance' in dir() else attr_name,
                    "has_data_spec": spec is not None,
                    "spec": spec,
                })

    return results


def _get_strategy_instance(class_name: str) -> Optional[SingleAssetStrategy]:
    """Get a strategy instance by class name."""
    for info in discover_strategies():
        if info["class_name"] == class_name:
            module = importlib.import_module(info["module"])
            cls = getattr(module, class_name)
            return cls()
    return None


def _get_strategy_status(strategy_name: str, spec: Optional[StrategyDataSpec]) -> dict:
    """Get the current data build status for a strategy."""
    folder = strategy_folder(strategy_name)
    manifest = load_manifest(strategy_name)

    status = {
        "has_folder": folder.exists(),
        "has_manifest": manifest is not None,
        "manifest": manifest,
        "errors": [],
        "ready": False,
    }

    if manifest and spec:
        errors = StrategyDataValidator.validate(strategy_name, spec)
        status["errors"] = errors
        status["ready"] = len(errors) == 0

    return status


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def strategy_page(request: Request):
    """Strategy data builder page."""
    strategies = discover_strategies()
    return templates.TemplateResponse("pages/strategy.html", {
        "request": request,
        "strategies": strategies,
        "active_tab": "strategy",
    })


@router.get("/spec/{class_name}", response_class=HTMLResponse)
async def strategy_spec(request: Request, class_name: str):
    """Return strategy spec details as an HTMX partial."""
    instance = _get_strategy_instance(class_name)
    if instance is None:
        return HTMLResponse(
            '<div class="text-red-400 text-sm p-4">Strategy not found</div>'
        )

    spec = instance.data_spec()
    if spec is None:
        return HTMLResponse(
            '<div class="text-yellow-400 text-sm p-4">This strategy does not define a data_spec() yet</div>'
        )

    status = _get_strategy_status(instance.name, spec)

    # Extract strategy description from docstring
    doc = instance.__class__.__doc__ or ""
    description = doc.strip().split("\n")[0] if doc.strip() else ""

    # Build line-by-line data requirements
    data_reqs = []
    for interval, indicators in spec.intervals.items():
        if not indicators:
            data_reqs.append({"interval": interval, "type": "OHLCV", "detail": "Price data only"})
        else:
            for ind_name, ind_params in indicators:
                param_str = ", ".join(f"{v}" for v in ind_params.values()) if ind_params else ""
                data_reqs.append({
                    "interval": interval,
                    "type": "indicator",
                    "name": ind_name.upper(),
                    "detail": f"{ind_name}({param_str})" if param_str else ind_name,
                    "warmup": spec.warmup_bars(interval),
                })

    return templates.TemplateResponse("partials/strategy/spec.html", {
        "request": request,
        "strategy_name": instance.name,
        "class_name": class_name,
        "spec": spec,
        "status": status,
        "description": description,
        "data_reqs": data_reqs,
    })


@router.get("/available-dates/{class_name}")
async def available_dates(class_name: str):
    """
    Return the available date range for a strategy's data requirements.

    Computes the intersection of available periods across all intervals,
    then offsets the earliest start by the warmup requirement so the user
    can only select start dates that guarantee warm indicators.
    """
    instance = _get_strategy_instance(class_name)
    if instance is None:
        return {"error": "Strategy not found"}

    spec = instance.data_spec()
    if spec is None:
        return {"error": "No data_spec()"}

    # Find available monthly periods per interval
    per_interval = {}
    for interval in spec.intervals:
        periods = list_available_periods(spec.venue, spec.market, spec.ticker, interval)
        # Normalise yearly periods to monthly (e.g. "2024" → "2024-01" .. "2024-12")
        monthly = []
        for p in periods:
            if len(p) == 4:  # yearly
                for m in range(1, 13):
                    monthly.append(f"{p}-{m:02d}")
            else:
                monthly.append(p)
        per_interval[interval] = set(monthly)

    if not per_interval:
        return {"months": [], "earliest_start": None, "latest_end": None}

    # Intersection: months available for ALL intervals
    common = set.intersection(*per_interval.values()) if per_interval else set()
    if not common:
        return {"months": [], "earliest_start": None, "latest_end": None}

    all_months = sorted(common)
    raw_earliest = all_months[0]
    latest_end = all_months[-1]

    # Offset earliest by warmup requirement
    warmup_months = spec.warmup_periods()
    if warmup_months > 0 and len(all_months) > warmup_months:
        earliest_start = all_months[warmup_months]
    else:
        earliest_start = raw_earliest

    # Per-interval availability (for the legend / tooltip)
    interval_ranges = {}
    for iv, months_set in per_interval.items():
        s = sorted(months_set)
        interval_ranges[iv] = {
            "months": s,
            "start": s[0] if s else None,
            "end": s[-1] if s else None,
            "count": len(s),
        }

    return {
        "months": all_months,
        "raw_earliest": raw_earliest,
        "earliest_start": earliest_start,
        "latest_end": latest_end,
        "warmup_months": warmup_months,
        "per_interval": interval_ranges,
    }


class DeleteRequest(BaseModel):
    class_name: str


@router.post("/delete")
async def delete_strategy_data(req: DeleteRequest):
    """Delete built data files for a strategy, allowing a fresh build."""
    import shutil

    instance = _get_strategy_instance(req.class_name)
    if instance is None:
        return {"success": False, "error": "Strategy not found"}

    folder = strategy_folder(instance.name)
    data_dir = folder / "data"
    results_dir = folder / "results"
    manifest_path = folder / "manifest.json"

    deleted = []
    for target in [data_dir, results_dir, manifest_path]:
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            deleted.append(str(target.name))

    return {"success": True, "deleted": deleted, "strategy_name": instance.name}


class BuildRequest(BaseModel):
    class_name: str
    start_date: str
    end_date: str


@router.post("/build")
async def build_strategy_data(req: BuildRequest):
    """Build data files for a strategy."""
    instance = _get_strategy_instance(req.class_name)
    if instance is None:
        return {"success": False, "error": "Strategy not found"}

    spec = instance.data_spec()
    if spec is None:
        return {"success": False, "error": "Strategy does not define data_spec()"}

    try:
        builder = StrategyDataBuilder(verbose=True)
        manifest = builder.build(
            strategy_name=instance.name,
            spec=spec,
            start_date=req.start_date,
            end_date=req.end_date,
        )

        # Validate after build
        errors = StrategyDataValidator.validate(instance.name, spec)

        return {
            "success": len(errors) == 0,
            "strategy_name": instance.name,
            "quality": manifest.get("quality", {}),
            "errors": errors,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Strategy data preview
# ---------------------------------------------------------------------------

# Indicator columns that should overlay on the price chart (same scale as price)
_PRICE_OVERLAY_PREFIXES = ("SMA_", "EMA_", "BB_", "VWAP")


@router.get("/preview/{class_name}/{interval}", response_class=HTMLResponse)
async def strategy_data_preview(
    request: Request,
    class_name: str,
    interval: str,
    page: int = 1,
    page_size: int = 100,
):
    """Preview a strategy's built parquet file with chart + table."""
    instance = _get_strategy_instance(class_name)
    if instance is None:
        return HTMLResponse('<div class="text-red-400 text-sm p-4">Strategy not found</div>')

    parquet_path = strategy_folder(instance.name) / "data" / f"{interval}.parquet"
    if not parquet_path.exists():
        return HTMLResponse(
            f'<div class="text-yellow-400 text-sm p-4">No data file for {interval}</div>'
        )

    df = pd.read_parquet(parquet_path)

    # Identify column groups
    ohlcv_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    # Extra raw columns (not indicators) — skip from indicator charts
    _raw_extras = {"quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "market_open"}
    indicator_cols = [c for c in df.columns if c not in ohlcv_cols and c not in _raw_extras]
    overlay_cols = [c for c in indicator_cols if any(c.startswith(p) for p in _PRICE_OVERLAY_PREFIXES)]
    separate_cols = [c for c in indicator_cols if c not in overlay_cols]

    # Prepare chart data (downsample if needed)
    chart_df = df
    max_points = 50000
    if len(chart_df) > max_points:
        step = len(chart_df) // max_points
        chart_df = chart_df.iloc[::step]

    chart_df = chart_df.fillna(0)
    timestamps = [t.isoformat() for t in chart_df.index]

    chart_data = {
        "timestamps": timestamps,
        "close": chart_df["close"].tolist() if "close" in chart_df.columns else [],
        "volume": chart_df["volume"].tolist() if "volume" in chart_df.columns else [],
        "overlays": {},
        "indicators": {},
    }
    for col in overlay_cols:
        chart_data["overlays"][col] = chart_df[col].tolist()
    for col in separate_cols:
        chart_data["indicators"][col] = chart_df[col].tolist()

    # Prepare table data (paginated)
    total_rows = len(df)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    table_df = df.iloc[start_idx:end_idx]

    all_cols = ohlcv_cols + indicator_cols
    table_data = []
    for ts, row in table_df.iterrows():
        rec = {"timestamp": ts.strftime("%Y-%m-%d %H:%M")}
        for col in all_cols:
            val = row[col]
            if pd.isna(val):
                rec[col] = "—"
            elif col == "volume":
                rec[col] = f"{val:,.0f}"
            elif isinstance(val, float):
                rec[col] = f"{val:.4f}" if abs(val) < 100 else f"{val:.2f}"
            else:
                rec[col] = str(val)
        table_data.append(rec)

    return templates.TemplateResponse("partials/strategy/data_preview.html", {
        "request": request,
        "class_name": class_name,
        "strategy_name": instance.name,
        "interval": interval,
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "all_cols": all_cols,
        "overlay_cols": overlay_cols,
        "separate_cols": separate_cols,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": total_pages,
        },
    })
