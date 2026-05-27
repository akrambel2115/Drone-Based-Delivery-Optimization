"""Instance endpoints.

GET /api/instances                 -> list of summaries
GET /api/instances/{name}/summary  -> one summary
GET /api/instances/{name}          -> full instance JSON
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.services.instance_cache import get_all_names, get_instance, get_summary

router = APIRouter(prefix="/api/instances", tags=["instances"])


@router.get("")
def list_instances():
    """Return a summary for every available benchmark instance."""
    return [get_summary(name) for name in get_all_names()]


@router.get("/{name}/summary")
def instance_summary(name: str):
    summary = get_summary(name)
    if summary is None:
        raise HTTPException(404, detail=f"Instance '{name}' not found")
    return summary


@router.get("/{name}")
def instance_detail(name: str):
    """Return the raw instance JSON (passthrough — the frontend needs all fields for map rendering)."""
    data = get_instance(name)
    if data is None:
        raise HTTPException(404, detail=f"Instance '{name}' not found")
    return JSONResponse(content=data)
