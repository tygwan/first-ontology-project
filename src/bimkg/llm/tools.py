"""Retrieval tools for the BIM LLM agent.

Each tool is a plain Python function that takes a query string and returns
a JSON-serializable result. LangChain wraps these as Tool objects.

Tools:
1. sql_query — run SQL on SQLite bimkg.db
2. text_search — FTS5 full-text search on display_name/pipeline/system_path
3. sparql_query — run SPARQL on OWL TBox+ABox (rdflib in-memory)
4. cypher_query — run Cypher on Neo4j (bolt connection)
5. kpi_summary — retrieve pre-computed KPIs for a zone or pipeline
"""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd
from rdflib import Graph as RDFGraph

from bimkg import config

# ---------------------------------------------------------------------------
# 1. SQL query
# ---------------------------------------------------------------------------

_SQLITE_PATH = str(config.SQLITE_BIMKG)

# Schema hint for LLM prompt
SQL_SCHEMA = """
Tables:
  bim_objects (12,009 rows) — columns include:
    object_id TEXT PK, display_name TEXT, refined_class TEXT,
    sp3d_pipeline TEXT, sp3d_pipe_run TEXT, sp3d_eqp_type_0 TEXT,
    sp3d_material TEXT, sp3d_spec_name TEXT,
    centroid_x REAL, centroid_y REAL, centroid_z REAL,
    dry_weight_kg REAL, length_m REAL, design_pressure_kpa REAL,
    design_temperature_c REAL, bbox_volume_m3 REAL,
    has_real_mesh BOOLEAN, is_container BOOLEAN, is_analysis_volume BOOLEAN,
    is_parent_box BOOLEAN, graph_participant BOOLEAN,
    classification_confidence TEXT, classification_confidence_reason TEXT,
    level INTEGER, system_path TEXT, parent_id TEXT

  bim_adjacency (220,346 rows):
    source_object_id TEXT, target_object_id TEXT,
    relation_type TEXT (overlap/touch/neartouch),
    distance_m REAL, overlap_volume_m3 REAL
"""


def sql_query(query: str) -> str:
    """Execute a read-only SQL query on bimkg.db and return results as JSON."""
    try:
        conn = sqlite3.connect(f"file:{_SQLITE_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query).fetchall()
        conn.close()
        results = [dict(r) for r in rows[:100]]  # cap at 100 rows
        return json.dumps(results, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# 2. Text search (FTS5)
# ---------------------------------------------------------------------------

FTS_TABLE = "bim_objects_fts"


def ensure_fts5() -> None:
    """Create FTS5 virtual table if it doesn't exist."""
    conn = sqlite3.connect(_SQLITE_PATH)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    if FTS_TABLE not in tables:
        conn.execute(f"""
            CREATE VIRTUAL TABLE {FTS_TABLE} USING fts5(
                object_id, display_name, sp3d_pipeline, system_path,
                content=bim_objects, content_rowid=rowid
            )
        """)
        conn.execute(f"""
            INSERT INTO {FTS_TABLE}(rowid, object_id, display_name, sp3d_pipeline, system_path)
            SELECT rowid, object_id, display_name, sp3d_pipeline, system_path FROM bim_objects
        """)
        conn.commit()
    conn.close()


def text_search(query: str) -> str:
    """Full-text search on display_name, pipeline, system_path. Returns matching objects."""
    try:
        ensure_fts5()
        conn = sqlite3.connect(f"file:{_SQLITE_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT object_id, display_name, sp3d_pipeline, system_path "
            f"FROM {FTS_TABLE} WHERE {FTS_TABLE} MATCH ? LIMIT 30",
            (query,)
        ).fetchall()
        conn.close()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# 3. SPARQL query
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_rdf_graph() -> RDFGraph:
    """Load TBox + objects ABox into rdflib (cached, ~15s first call)."""
    g = RDFGraph()
    g.parse(str(config.ONTOLOGY_OWL), format="turtle")
    g.parse(str(config.ONTOLOGY_OWL_DIR / "bim-shared.ttl"), format="turtle")
    g.parse(str(config.ONTOLOGY_OWL_DIR / "bim-objects.ttl"), format="turtle")
    return g


SPARQL_SCHEMA = """
Namespaces:
  bim: <http://example.org/bim-ontology/>
  inst: <http://example.org/bim-ontology/instance/>

Classes: BIMEntity, BIMObject, PhysicalObject, PipingComponent, StructuralMember,
  Equipment, ElectricalComponent, HvacComponent, UncategorizedObject,
  Container, HierarchyNode, AnalysisArtifact, AnalysisVolume,
  Pipeline, PipeRun, Level, Material, Specification

Object properties: adjacentTo (symmetric), hasParent, belongsToPipeline,
  belongsToPipeRun, hasMaterial, hasSpecification, atLevel, inGroup

Data properties: objectId, displayName, systemPath, level, refinedClass,
  classificationConfidence, centroidX/Y/Z, bboxVolumeM3, dryWeightKg,
  lengthM, designPressureKpa, designTemperatureC, hasRealMesh, isContainer,
  isAnalysisVolume, commodityCode, npd, specName
"""


def sparql_query(query: str) -> str:
    """Execute a SPARQL SELECT query on the OWL graph. Returns bindings as JSON."""
    try:
        g = _load_rdf_graph()
        results = g.query(query)
        rows = []
        for row in list(results)[:100]:
            rows.append({str(k): str(v) for k, v in zip(results.vars, row)})
        return json.dumps(rows, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# 4. Cypher query (Neo4j)
# ---------------------------------------------------------------------------

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "bimkg2026"

CYPHER_SCHEMA = """
Node labels: BIMObject (objectId, displayName, refinedClass, centroidX/Y/Z,
  dryWeightKg, confidence, criticalStep, onCriticalPath),
  Pipeline (pipelineId, name), Zone (zoneId, zoneNumber, installRank,
  objectCount, equipmentCount, totalWeightKg)

Relationships:
  (:BIMObject)-[:ADJACENT_TO {relationType, distanceM, overlapM3}]->(:BIMObject)
  (:BIMObject)-[:MUST_PRECEDE {edgeType, onCriticalPath}]->(:BIMObject)
  (:BIMObject)-[:HAS_PARENT]->(:BIMObject)
  (:BIMObject)-[:BELONGS_TO_PIPELINE]->(:Pipeline)
  (:BIMObject)-[:IN_ZONE]->(:Zone)
  (:Zone)-[:ZONE_PRECEDES {dependencies}]->(:Zone)
"""


def cypher_query(query: str) -> str:
    """Execute a Cypher query on Neo4j. Returns records as JSON."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        with driver.session() as session:
            result = session.run(query)
            records = [dict(r) for r in result][:100]
        driver.close()
        # Serialize Neo4j types
        def _serialize(obj):
            if hasattr(obj, "items"):
                return dict(obj)
            return str(obj)
        return json.dumps(records, ensure_ascii=False, default=_serialize)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# 5. KPI summary
# ---------------------------------------------------------------------------


def kpi_summary(query: str) -> str:
    """Look up KPIs for a zone or pipeline.

    Input: "zone 15" or "pipeline P-10147" or "plant"
    """
    try:
        gold = pd.read_parquet(config.ENRICHED_OBJECTS)
        parts = query.strip().lower().split()

        if parts[0] == "plant":
            phys = gold[gold["graph_participant"] == True]
            result = {
                "total_objects": len(gold),
                "physical_objects": len(phys),
                "total_weight_tonnes": round(phys["dry_weight_kg"].sum() / 1000, 1),
                "pipelines": gold["sp3d_pipeline"].nunique(),
                "classes": gold["refined_class"].value_counts().to_dict(),
            }
        elif parts[0] == "pipeline" and len(parts) > 1:
            pipe_name = " ".join(parts[1:])
            # Try exact match first, then case-insensitive
            pipe = gold[gold["sp3d_pipeline"] == pipe_name]
            if pipe.empty:
                pipe = gold[gold["sp3d_pipeline"].str.lower() == pipe_name.lower()]
            if pipe.empty:
                return json.dumps({"error": f"Pipeline '{pipe_name}' not found"})
            result = {
                "pipeline": pipe["sp3d_pipeline"].iloc[0],
                "object_count": len(pipe),
                "total_weight_kg": round(pipe["dry_weight_kg"].sum(), 1),
                "classes": pipe["refined_class"].value_counts().to_dict(),
                "pipe_runs": pipe["sp3d_pipe_run"].nunique(),
                "mean_z": round(pipe["centroid_z"].mean(), 1),
            }
        elif parts[0] == "zone" and len(parts) > 1:
            zone_id = parts[1]
            # Zone info from gold (need zone_map — use graph_participant objects)
            result = {"info": "Zone lookup requires zone_map. Use sql_query for zone analysis."}
        else:
            result = {"usage": "Input: 'plant', 'pipeline P-10147', or 'zone 15'"}

        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
