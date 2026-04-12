"""FastAPI backend for BIM Knowledge Graph.

Exposes the data pipeline's outputs as REST endpoints:
- /objects — BIM object queries (SQL)
- /search — full-text search (FTS5)
- /graph — adjacency, neighbors, precedence (SQL + Neo4j)
- /ontology — SPARQL queries, class hierarchy
- /kpi — pre-computed KPIs at plant/zone/pipeline level
- /llm — natural language query via LangGraph agent

Run: uvicorn bimkg.api.main:app --reload
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from bimkg.llm.tools import (
    sql_query as _sql_query,
    text_search as _text_search,
    sparql_query as _sparql_query,
    cypher_query as _cypher_query,
    kpi_summary as _kpi_summary,
)

app = FastAPI(
    title="BIM Knowledge Graph API",
    description="REST API for SP3D plant BIM data (12,009 objects, 477K OWL triples, Neo4j 261K edges)",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# /objects — SQL-based object queries
# ---------------------------------------------------------------------------


@app.get("/objects", tags=["objects"])
def list_objects(
    refined_class: str | None = Query(None, description="Filter by class (Piping, Structure, etc.)"),
    pipeline: str | None = Query(None, description="Filter by pipeline name"),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List BIM objects with optional filters."""
    conditions = []
    if refined_class:
        conditions.append(f"refined_class = '{refined_class}'")
    if pipeline:
        conditions.append(f"sp3d_pipeline = '{pipeline}'")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT object_id, display_name, refined_class, sp3d_pipeline, dry_weight_kg, centroid_x, centroid_y, centroid_z FROM bim_objects {where} LIMIT {limit} OFFSET {offset}"
    return json.loads(_sql_query(sql))


@app.get("/objects/{object_id}", tags=["objects"])
def get_object(object_id: str) -> dict:
    """Get a single object by ID."""
    result = json.loads(_sql_query(
        f"SELECT * FROM bim_objects WHERE object_id = '{object_id}'"
    ))
    if not result:
        raise HTTPException(404, f"Object {object_id} not found")
    return result[0]


@app.get("/objects/{object_id}/neighbors", tags=["objects"])
def get_neighbors(
    object_id: str,
    relation_type: str | None = Query(None, description="Filter: touch, overlap, neartouch"),
    limit: int = Query(20, le=100),
) -> list[dict]:
    """Get adjacent objects."""
    cond = f"AND a.relation_type = '{relation_type}'" if relation_type else ""
    sql = f"""
        SELECT b.object_id, b.display_name, b.refined_class,
               a.relation_type, a.distance_m, a.overlap_volume_m3
        FROM bim_adjacency a
        JOIN bim_objects b ON a.target_object_id = b.object_id
        WHERE a.source_object_id = '{object_id}' {cond}
        LIMIT {limit}
    """
    return json.loads(_sql_query(sql))


# ---------------------------------------------------------------------------
# /search — full-text search
# ---------------------------------------------------------------------------


@app.get("/search", tags=["search"])
def search(q: str = Query(..., description="Search terms")) -> list[dict]:
    """Full-text search on display_name, pipeline, system_path."""
    return json.loads(_text_search(q))


# ---------------------------------------------------------------------------
# /graph — Neo4j queries
# ---------------------------------------------------------------------------


class CypherRequest(BaseModel):
    query: str


@app.post("/graph/cypher", tags=["graph"])
def run_cypher(req: CypherRequest) -> Any:
    """Execute a read-only Cypher query on Neo4j."""
    if any(kw in req.query.upper() for kw in ["DELETE", "CREATE", "SET", "MERGE", "DROP"]):
        raise HTTPException(400, "Write operations not allowed")
    return json.loads(_cypher_query(req.query))


@app.get("/graph/pipelines", tags=["graph"])
def list_pipelines() -> list[dict]:
    """List all pipelines with object counts."""
    sql = """
        SELECT sp3d_pipeline AS name, count(*) AS object_count,
               sum(dry_weight_kg) AS total_weight_kg
        FROM bim_objects WHERE sp3d_pipeline IS NOT NULL
        GROUP BY sp3d_pipeline ORDER BY object_count DESC
    """
    return json.loads(_sql_query(sql))


@app.get("/graph/classes", tags=["graph"])
def class_distribution() -> list[dict]:
    """Get class distribution."""
    sql = "SELECT refined_class, count(*) AS cnt FROM bim_objects GROUP BY refined_class ORDER BY cnt DESC"
    return json.loads(_sql_query(sql))


# ---------------------------------------------------------------------------
# /ontology — SPARQL
# ---------------------------------------------------------------------------


class SparqlRequest(BaseModel):
    query: str


@app.post("/ontology/sparql", tags=["ontology"])
def run_sparql(req: SparqlRequest) -> Any:
    """Execute a SPARQL SELECT query on the OWL graph."""
    return json.loads(_sparql_query(req.query))


# ---------------------------------------------------------------------------
# /kpi — pre-computed KPIs
# ---------------------------------------------------------------------------


@app.get("/kpi/plant", tags=["kpi"])
def plant_kpi() -> dict:
    """Plant-level KPI summary."""
    return json.loads(_kpi_summary("plant"))


@app.get("/kpi/pipeline/{name}", tags=["kpi"])
def pipeline_kpi(name: str) -> dict:
    """Pipeline-level KPI summary."""
    result = json.loads(_kpi_summary(f"pipeline {name}"))
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ---------------------------------------------------------------------------
# /llm — natural language query
# ---------------------------------------------------------------------------


class LlmRequest(BaseModel):
    question: str


_agent = None


@app.post("/llm/query", tags=["llm"])
def llm_query(req: LlmRequest) -> dict:
    """Natural language query via LangGraph agent."""
    global _agent
    if _agent is None:
        if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
            raise HTTPException(503, "No LLM API key configured (GOOGLE_API_KEY or ANTHROPIC_API_KEY)")
        from bimkg.llm.agent import create_bim_agent
        provider = "google" if os.environ.get("GOOGLE_API_KEY") else "anthropic"
        _agent = create_bim_agent(provider=provider)

    from bimkg.llm.agent import ask
    answer = ask(req.question, _agent)
    return {"question": req.question, "answer": answer}
