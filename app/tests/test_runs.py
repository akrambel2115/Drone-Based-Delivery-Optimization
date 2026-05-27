"""Tests for the /api/runs endpoints."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _wait_for_done(run_id: str, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "done":
            return data
        if data["status"] == "error":
            pytest.fail(f"Run failed: {data['error']}")
        time.sleep(0.5)
    pytest.fail("Run did not finish in time")


def test_create_run_sa():
    body = {
        "instance": "instance_01_basic_small",
        "algorithm": "sa",
        "config": {
            "initial_temperature": 50.0,
            "min_temperature": 1.0,
            "cooling_rate": 0.9,
            "inner_iterations": 50,
            "max_iterations": 500,
            "record_history": True,
        },
    }
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data

    run_data = _wait_for_done(data["run_id"])
    result = run_data["result"]
    assert result is not None
    assert result["feasible"] is True
    assert result["best_energy"] > 0
    assert len(result["best_solution"]["routes"]) > 0


def test_create_run_ga():
    body = {
        "instance": "instance_01_basic_small",
        "algorithm": "ga",
        "config": {
            "population_size": 10,
            "generations": 5,
            "record_history": True,
        },
    }
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    run_data = _wait_for_done(run_id)
    result = run_data["result"]
    assert result["best_energy"] > 0


def test_list_runs():
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_run_not_found():
    resp = client.get("/api/runs/does-not-exist")
    assert resp.status_code == 404
