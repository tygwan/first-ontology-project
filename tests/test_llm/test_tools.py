"""Tests for bimkg.llm.tools (retrieval functions)."""

from __future__ import annotations

import json

import pytest

from bimkg import config
from bimkg.llm.tools import (
    sql_query,
    text_search,
    sparql_query,
    kpi_summary,
    ensure_fts5,
)


@pytest.fixture(scope="module", autouse=True)
def _check_data():
    if not config.SQLITE_BIMKG.exists():
        pytest.skip("SQLite DB not found")


class TestSqlQuery:
    def test_count_objects(self) -> None:
        result = json.loads(sql_query("SELECT count(*) AS cnt FROM bim_objects"))
        assert result[0]["cnt"] == config.EXPECTED_OBJECT_COUNT

    def test_class_distribution(self) -> None:
        result = json.loads(sql_query(
            "SELECT refined_class, count(*) AS cnt FROM bim_objects GROUP BY refined_class"
        ))
        classes = {r["refined_class"]: r["cnt"] for r in result}
        assert classes["Piping"] == 3062
        assert classes["Structure"] == 4840

    def test_invalid_sql_returns_error(self) -> None:
        result = json.loads(sql_query("DROP TABLE bim_objects"))
        assert "error" in result

    def test_write_blocked(self) -> None:
        result = json.loads(sql_query("INSERT INTO bim_objects (object_id) VALUES ('x')"))
        assert "error" in result


class TestTextSearch:
    def test_search_blind_flange(self) -> None:
        ensure_fts5()
        result = json.loads(text_search("Blind Flange"))
        assert len(result) > 0
        assert any("Blind" in r.get("display_name", "") for r in result)

    def test_search_pipeline(self) -> None:
        ensure_fts5()
        result = json.loads(text_search("P-10147"))
        assert len(result) >= 1


class TestSparqlQuery:
    def test_count_piping(self) -> None:
        if not config.ONTOLOGY_OWL.exists():
            pytest.skip("OWL files not found")
        result = json.loads(sparql_query("""
            PREFIX bim: <http://example.org/bim-ontology/>
            SELECT (COUNT(?s) AS ?cnt) WHERE { ?s a bim:PipingComponent }
        """))
        assert int(result[0]["cnt"]) > 2000

    def test_invalid_sparql_returns_error(self) -> None:
        result = json.loads(sparql_query("NOT VALID SPARQL"))
        assert "error" in result


class TestKpiSummary:
    def test_plant_summary(self) -> None:
        result = json.loads(kpi_summary("plant"))
        assert result["total_objects"] == config.EXPECTED_OBJECT_COUNT
        assert result["total_weight_tonnes"] > 1000

    def test_pipeline_lookup(self) -> None:
        result = json.loads(kpi_summary("pipeline P-10147"))
        assert result["object_count"] == 129

    def test_unknown_pipeline(self) -> None:
        result = json.loads(kpi_summary("pipeline NONEXISTENT"))
        assert "error" in result
