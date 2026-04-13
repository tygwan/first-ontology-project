"""BIM Knowledge Graph Pipeline — Airflow DAG.

Converts the manual function calls (run_phase_1a, run_powerbi_export,
run_foundry_export, generate_tbox, generate_abox, etc.) into an Airflow
DAG with dataset lineage tracking via inlets/outlets.

Pipeline:
    Bronze (raw) → Silver (clean) → Gold (enriched)
                                      ├── PowerBI export
                                      ├── Foundry export
                                      ├── OWL ontology (TBox + ABox)
                                      ├── Neo4j CSV export
                                      └── Graph analytics (KPIs)

Airflow 3.x: `Dataset` was renamed to `Asset` (lives in `airflow.sdk`).
We keep the local alias `Dataset = Asset` so the DAG reads naturally.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project src to path (for local Airflow runs)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airflow.sdk import DAG, Asset as Dataset
from airflow.providers.standard.operators.python import PythonOperator

# ---------------------------------------------------------------------------
# Datasets — Airflow Dataset URIs for lineage tracking
# ---------------------------------------------------------------------------

SNAPSHOT = "2026-04-12"
DATA = PROJECT_ROOT / "data"

# Bronze (sources) — these are external; we declare them as inputs only
DATASET_BRONZE_XLSX = Dataset(f"file://{DATA}/raw/dxtnavis/{SNAPSHOT}/Refining_ObjectID_20260412_064240.xlsx")
DATASET_BRONZE_PROPS = Dataset(f"file://{DATA}/raw/dxtnavis/{SNAPSHOT}/AllProperties_20260407_184650.csv")
DATASET_BRONZE_ADJ = Dataset(f"file://{DATA}/raw/dxtnavis/{SNAPSHOT}/adjacency.csv")
DATASET_BRONZE_GEOM = Dataset(f"file://{DATA}/raw/dxtnavis/{SNAPSHOT}/geometry.csv")
DATASET_BRONZE_VAL = Dataset(f"file://{DATA}/raw/dxtnavis/{SNAPSHOT}/validation.csv")
DATASET_BRONZE_GROUPS = Dataset(f"file://{DATA}/raw/dxtnavis/{SNAPSHOT}/connected_groups.csv")

# Gold (Phase 1a output)
DATASET_GOLD_OBJECTS = Dataset(f"file://{DATA}/enriched/{SNAPSHOT}/bim_objects_enriched.parquet")
DATASET_GOLD_ADJACENCY = Dataset(f"file://{DATA}/enriched/{SNAPSHOT}/bim_adjacency_sym.parquet")
DATASET_GOLD_SQLITE = Dataset(f"file://{DATA}/enriched/{SNAPSHOT}/bimkg.db")

# Output (Phase 1d, 2, 4)
DATASET_POWERBI = Dataset(f"file://{DATA}/powerbi/{SNAPSHOT}/")
DATASET_FOUNDRY = Dataset(f"file://{DATA}/ontology/{SNAPSHOT}/object_types/")
DATASET_OWL_TBOX = Dataset(f"file://{DATA}/ontology/{SNAPSHOT}/owl/bim-ontology.owl")
DATASET_OWL_ABOX = Dataset(f"file://{DATA}/ontology/{SNAPSHOT}/owl/bim-objects.ttl")
DATASET_NEO4J = Dataset(f"file://{DATA}/ontology/{SNAPSHOT}/neo4j/")
DATASET_SHAPES = Dataset(f"file://{DATA}/ontology/{SNAPSHOT}/owl/bim-shapes.ttl")


# ---------------------------------------------------------------------------
# Task functions — wrap existing pipeline functions
# ---------------------------------------------------------------------------


def task_phase_1a():
    """Phase 1a: Bronze → Silver → Gold parquet + SQLite."""
    from bimkg.ingest.sqlite_writer import run_phase_1a
    run_phase_1a()


def task_phase_1d_powerbi():
    """Phase 1d: Gold → PowerBI 10 CSV."""
    from bimkg.ingest.exporters.powerbi import run_powerbi_export
    run_powerbi_export()


def task_phase_1d_foundry():
    """Phase 1d: Gold → Foundry 10 parquet."""
    from bimkg.ingest.exporters.foundry import run_foundry_export
    run_foundry_export()


def task_phase_2_tbox():
    """Phase 2: Generate OWL TBox."""
    from bimkg.ontology.schema import generate_tbox
    generate_tbox()


def task_phase_2_abox():
    """Phase 2: Generate OWL ABox (3 TTL files)."""
    from bimkg.ontology.instances import generate_abox
    generate_abox()


def task_phase_3_shacl():
    """Phase 3: Generate SHACL shapes."""
    from bimkg.validation.shapes import generate_shapes
    generate_shapes()


def task_phase_4_neo4j():
    """Phase 4: Generate Neo4j CSV exports."""
    import pandas as pd
    from bimkg import config
    from bimkg.analytics.metrics import build_physical_graph
    from bimkg.analytics.zones import assign_louvain_zones
    from bimkg.analytics.precedence import build_precedence_dag
    from bimkg.analytics.neo4j_export import export_neo4j

    gold = pd.read_parquet(config.ENRICHED_OBJECTS)
    adj = pd.read_parquet(config.ENRICHED_ADJACENCY_SYM)
    G = build_physical_graph(gold, adj)
    zone_map = assign_louvain_zones(G, resolution=3.0)
    gold["zone_id"] = gold["object_id"].map(zone_map)
    dag = build_precedence_dag(gold, adj, zone_col="zone_id")
    export_neo4j(gold, adj, precedence_dag=dag, zone_map=zone_map)


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

default_args = {
    "owner": "bimkg",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bim_pipeline",
    description="BIM Knowledge Graph end-to-end pipeline (DXTnavis → OWL/Neo4j/Foundry/PowerBI)",
    start_date=datetime(2026, 4, 1),
    schedule=None,  # manual / data-driven
    catchup=False,
    default_args=default_args,
    tags=["bim", "ontology", "medallion"],
) as dag:

    phase_1a = PythonOperator(
        task_id="phase_1a_silver_gold",
        python_callable=task_phase_1a,
        inlets=[
            DATASET_BRONZE_XLSX,
            DATASET_BRONZE_PROPS,
            DATASET_BRONZE_ADJ,
            DATASET_BRONZE_GEOM,
            DATASET_BRONZE_VAL,
            DATASET_BRONZE_GROUPS,
        ],
        outlets=[DATASET_GOLD_OBJECTS, DATASET_GOLD_ADJACENCY, DATASET_GOLD_SQLITE],
        doc_md="""
### Phase 1a — Silver + Gold

Reads 6 Bronze CSV/XLSX files, applies XLSX classifier (PR #3 negative
lookahead), unit conversion (imperial → SI), column rename, derived flags
(is_container, is_analysis_volume, is_parent_box), confidence layer.

**Output**: 12,009 rows × 219 cols Gold parquet + SQLite database.
        """,
    )

    phase_1d_powerbi = PythonOperator(
        task_id="phase_1d_powerbi",
        python_callable=task_phase_1d_powerbi,
        inlets=[DATASET_GOLD_OBJECTS],
        outlets=[DATASET_POWERBI],
    )

    phase_1d_foundry = PythonOperator(
        task_id="phase_1d_foundry",
        python_callable=task_phase_1d_foundry,
        inlets=[DATASET_GOLD_OBJECTS, DATASET_GOLD_ADJACENCY],
        outlets=[DATASET_FOUNDRY],
    )

    phase_2_tbox = PythonOperator(
        task_id="phase_2_owl_tbox",
        python_callable=task_phase_2_tbox,
        outlets=[DATASET_OWL_TBOX],
    )

    phase_2_abox = PythonOperator(
        task_id="phase_2_owl_abox",
        python_callable=task_phase_2_abox,
        inlets=[DATASET_GOLD_OBJECTS, DATASET_GOLD_ADJACENCY, DATASET_OWL_TBOX],
        outlets=[DATASET_OWL_ABOX],
    )

    phase_3_shacl = PythonOperator(
        task_id="phase_3_shacl_shapes",
        python_callable=task_phase_3_shacl,
        outlets=[DATASET_SHAPES],
    )

    phase_4_neo4j = PythonOperator(
        task_id="phase_4_neo4j_export",
        python_callable=task_phase_4_neo4j,
        inlets=[DATASET_GOLD_OBJECTS, DATASET_GOLD_ADJACENCY],
        outlets=[DATASET_NEO4J],
    )

    # Dependencies
    phase_1a >> [phase_1d_powerbi, phase_1d_foundry, phase_2_tbox, phase_4_neo4j]
    [phase_1a, phase_2_tbox] >> phase_2_abox
    phase_2_tbox >> phase_3_shacl
