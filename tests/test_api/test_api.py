"""Tests for bimkg.api.main (FastAPI endpoints)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bimkg import config
from bimkg.api.main import app


@pytest.fixture(scope="module")
def client():
    if not config.SQLITE_BIMKG.exists():
        pytest.skip("SQLite DB not found")
    return TestClient(app)


class TestObjects:
    def test_list_objects(self, client) -> None:
        resp = client.get("/objects?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_filter_by_class(self, client) -> None:
        resp = client.get("/objects?refined_class=Equipment&limit=3")
        assert resp.status_code == 200
        for obj in resp.json():
            assert obj["refined_class"] == "Equipment"

    def test_filter_by_pipeline(self, client) -> None:
        resp = client.get("/objects?pipeline=P-10147&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_get_object_not_found(self, client) -> None:
        resp = client.get("/objects/nonexistent-id")
        assert resp.status_code == 404

    def test_get_neighbors(self, client) -> None:
        # Get a real object_id first
        objs = client.get("/objects?limit=1").json()
        oid = objs[0]["object_id"]
        resp = client.get(f"/objects/{oid}/neighbors?limit=5")
        assert resp.status_code == 200


class TestSearch:
    def test_search_blind_flange(self, client) -> None:
        resp = client.get("/search?q=Blind+Flange")
        assert resp.status_code == 200
        assert len(resp.json()) > 0


class TestGraph:
    def test_class_distribution(self, client) -> None:
        resp = client.get("/graph/classes")
        assert resp.status_code == 200
        classes = {r["refined_class"]: r["cnt"] for r in resp.json()}
        assert classes["Piping"] == 3062

    def test_list_pipelines(self, client) -> None:
        resp = client.get("/graph/pipelines")
        assert resp.status_code == 200
        assert len(resp.json()) >= 100  # capped at 100 by sql_query

    def test_cypher_write_blocked(self, client) -> None:
        resp = client.post("/graph/cypher", json={"query": "CREATE (n:Test)"})
        assert resp.status_code == 400


class TestKpi:
    def test_plant_kpi(self, client) -> None:
        resp = client.get("/kpi/plant")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_objects"] == config.EXPECTED_OBJECT_COUNT

    def test_pipeline_kpi(self, client) -> None:
        resp = client.get("/kpi/pipeline/P-10147")
        assert resp.status_code == 200
        assert resp.json()["object_count"] == 129

    def test_pipeline_not_found(self, client) -> None:
        resp = client.get("/kpi/pipeline/NONEXISTENT")
        assert resp.status_code == 404


class TestDocs:
    def test_openapi_docs(self, client) -> None:
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self, client) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/objects" in schema["paths"]
        assert "/llm/query" in schema["paths"]
