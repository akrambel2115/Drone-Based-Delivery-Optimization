"""Tests for the /api/instances endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_instances():
    resp = client.get("/api/instances")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 10
    for item in items:
        assert "name" in item
        assert "customers" in item
        assert "nfzs" in item


def test_instance_summary():
    resp = client.get("/api/instances/instance_01_basic_small/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["customers"] == 12
    assert data["fleet"] is None


def test_instance_summary_not_found():
    resp = client.get("/api/instances/nonexistent/summary")
    assert resp.status_code == 404


def test_instance_detail():
    resp = client.get("/api/instances/instance_01_basic_small")
    assert resp.status_code == 200
    data = resp.json()
    assert "depot" in data
    assert "customers" in data
    assert len(data["customers"]) == 12
