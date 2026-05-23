"""FastAPI application entry point for the Drone Delivery Cockpit.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import instances, runs

app = FastAPI(
    title="Drone Delivery Cockpit API",
    description="Backend for the interactive drone routing optimisation web app.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(instances.router)
app.include_router(runs.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
