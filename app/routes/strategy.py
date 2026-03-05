"""
Strategy Data Builder Routes

Web UI for discovering strategies, building data files, and managing strategy folders.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.strategy.base import SingleAssetStrategy
from core.strategy.data import (
    StrategyDataSpec,
    StrategyDataBuilder,
    StrategyDataValidator,
    strategy_folder,
    load_manifest,
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

    return templates.TemplateResponse("partials/strategy/spec.html", {
        "request": request,
        "strategy_name": instance.name,
        "class_name": class_name,
        "spec": spec,
        "status": status,
    })


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
