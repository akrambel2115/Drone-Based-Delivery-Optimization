"""Run endpoints.

POST /api/runs                   -> { run_id }
GET  /api/runs                   -> list of finished run summaries
GET  /api/runs/{run_id}          -> status + optional result
GET  /api/runs/{run_id}/stream   -> SSE stream of progress events
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.schemas.run import GAConfigIn, RunRequest, SAConfigIn
from app.services.solver_runner import get_job, list_jobs, load_saved_runs, submit_run

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("")
def create_run(body: RunRequest):
    """Submit a new solver run and return its run_id."""
    config_dict = body.config.model_dump()
    run_id = submit_run(body.instance, body.algorithm, config_dict)
    return {"run_id": run_id}


@router.get("")
def list_runs():
    """Return metadata for all runs — in-memory jobs first, then disk-saved runs."""
    seen: set[str] = set()
    items = []

    for job in sorted(list_jobs(), key=lambda j: j.started_at, reverse=True):
        seen.add(job.run_id)
        energy = None
        drones = None
        runtime = None
        if job.result:
            energy = job.result.get("best_energy")
            drones = job.result.get("num_routes")
            runtime = job.result.get("runtime_seconds")
        items.append(
            {
                "run_id": job.run_id,
                "instance": job.instance,
                "algorithm": job.algorithm,
                "energy": energy,
                "drones": drones,
                "runtime": runtime,
                "ts": job.started_at,
                "status": job.status,
            }
        )

    # Supplement with disk-saved runs not already in memory
    for saved in load_saved_runs():
        rid = saved.get("run_id")
        if rid and rid not in seen:
            seen.add(rid)
            items.append(
                {
                    "run_id": rid,
                    "instance": saved.get("instance_name", ""),
                    "algorithm": saved.get("algorithm", ""),
                    "energy": saved.get("best_energy"),
                    "drones": saved.get("num_routes"),
                    "runtime": saved.get("runtime_seconds"),
                    "ts": saved.get("submitted_at", 0),
                    "status": "done",
                }
            )

    return items


@router.get("/{run_id}")
def get_run(run_id: str):
    """Return current status and (when finished) the full result payload."""
    job = get_job(run_id)

    # Fall back to disk if not in memory (e.g. after server restart)
    if job is None:
        from pathlib import Path

        path = Path("data/solver_runs") / f"{run_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                "run_id": run_id,
                "status": "done",
                "instance": data.get("instance_name", ""),
                "algorithm": data.get("algorithm", ""),
                "progress": None,
                "best_energy_so_far": data.get("best_energy"),
                "result": data,
                "error": None,
                "started_at": data.get("submitted_at", 0),
                "finished_at": data.get("submitted_at", 0),
            }
        raise HTTPException(404, detail=f"Run '{run_id}' not found")

    best_so_far = None
    if job.progress_events:
        for ev in reversed(job.progress_events):
            if ev.get("type") == "progress":
                best_so_far = ev.get("best_energy")
                break

    return {
        "run_id": job.run_id,
        "status": job.status,
        "instance": job.instance,
        "algorithm": job.algorithm,
        "progress": len(job.progress_events),
        "best_energy_so_far": best_so_far,
        "result": job.result,
        "error": job.error,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    """SSE endpoint that streams progress events as they are produced by the solver thread."""
    job = get_job(run_id)
    if job is None:
        raise HTTPException(404, detail=f"Run '{run_id}' not found")

    async def event_generator():
        last_sent = 0
        while True:
            events = job.progress_events
            new_events = events[last_sent:]
            for ev in new_events:
                yield {"data": json.dumps(ev)}
                last_sent += 1
                if ev.get("type") == "done" or ev.get("type") == "error":
                    return

            if job.status in ("done", "error") and last_sent >= len(job.progress_events):
                # Ensure a terminal event is always sent
                yield {"data": json.dumps({"type": "done", "iteration": 0, "best_energy": 0.0, "temperature": None})}
                return

            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())
