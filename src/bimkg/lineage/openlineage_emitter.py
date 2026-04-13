"""OpenLineage event emitter for the BIM pipeline.

Produces JSONL of OpenLineage v2 events for each Phase of the pipeline so
external tools (Marquez, DataHub, Atlan, Foundry Lineage view, etc.) can
ingest the lineage graph without requiring a live Airflow run.

Why standalone, not airflow-openlineage:
    - openlineage-airflow needs a running scheduler. We want a static
      lineage artifact that ships with the repo for portfolio review.
    - The events here mirror what airflow-openlineage would emit, including
      Schema, ColumnLineage, Statistics, JobType, and SourceCode facets.

Output:
    data/lineage/{SNAPSHOT}/openlineage-events.jsonl
        — one OpenLineage event per line (START + COMPLETE for each Phase)

    data/lineage/{SNAPSHOT}/openlineage-summary.json
        — human-readable index of jobs/datasets/facets
"""

from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openlineage.client.event_v2 import (
    InputDataset,
    Job,
    OutputDataset,
    Run,
    RunEvent,
    RunState,
)
from openlineage.client.facet_v2 import (
    column_lineage_dataset,
    datasource_dataset,
    documentation_dataset,
    input_statistics_input_dataset,
    job_type_job,
    nominal_time_run,
    output_statistics_output_dataset,
    ownership_job,
    processing_engine_run,
    schema_dataset,
    source_code_location_job,
)
from openlineage.client.serde import Serde

from bimkg import config

PRODUCER = "https://github.com/tygwan/first-ontology-project/lineage/v0.2.0"
NS_FILE = f"file://{config.PROJECT_ROOT}"
NS_SQLITE = f"sqlite://{config.SQLITE_BIMKG}"
NS_FOUNDRY = "palantir-foundry://datayoon.usw-18.palantirfoundry.com"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_rev() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=config.PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def _file_size(p: Path) -> int | None:
    return p.stat().st_size if p.exists() else None


def _parquet_schema(path: Path) -> list[schema_dataset.SchemaDatasetFacetFields]:
    """Read parquet schema and return as OpenLineage SchemaDatasetFacet fields."""
    if not path.exists():
        return []
    df = pd.read_parquet(path)
    fields = []
    for col, dtype in df.dtypes.items():
        fields.append(
            schema_dataset.SchemaDatasetFacetFields(
                name=str(col),
                type=str(dtype),
            )
        )
    return fields


def _parquet_rowcount(path: Path) -> int | None:
    if not path.exists():
        return None
    return len(pd.read_parquet(path, columns=[]))


def _csv_schema(path: Path, sample_rows: int = 100) -> list[schema_dataset.SchemaDatasetFacetFields]:
    if not path.exists():
        return []
    df = pd.read_csv(path, nrows=sample_rows)
    return [
        schema_dataset.SchemaDatasetFacetFields(name=str(c), type=str(t))
        for c, t in df.dtypes.items()
    ]


def _csv_rowcount(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for _ in f) - 1  # subtract header


def _xlsx_schema(path: Path) -> list[schema_dataset.SchemaDatasetFacetFields]:
    if not path.exists():
        return []
    try:
        df = pd.read_excel(path, nrows=10)
        return [
            schema_dataset.SchemaDatasetFacetFields(name=str(c), type=str(t))
            for c, t in df.dtypes.items()
        ]
    except Exception:
        return []


def _job_facets(description: str, source_path: str) -> dict[str, Any]:
    git_rev = _git_rev()
    return {
        "jobType": job_type_job.JobTypeJobFacet(
            processingType="BATCH",
            integration="PYTHON",
            jobType="PIPELINE",
            producer=PRODUCER,
        ),
        "documentation": documentation_dataset.DocumentationDatasetFacet(
            description=description,
            producer=PRODUCER,
        ),
        "ownership": ownership_job.OwnershipJobFacet(
            owners=[ownership_job.Owner(name="bimkg-team", type="MAINTAINER")],
            producer=PRODUCER,
        ),
        "sourceCodeLocation": source_code_location_job.SourceCodeLocationJobFacet(
            type="git",
            url=f"https://github.com/tygwan/first-ontology-project/blob/{git_rev}/{source_path}",
            repoUrl="https://github.com/tygwan/first-ontology-project",
            path=source_path,
            version=git_rev,
            branch="main",
            producer=PRODUCER,
        ),
    }


def _run_facets() -> dict[str, Any]:
    return {
        "nominalTime": nominal_time_run.NominalTimeRunFacet(
            nominalStartTime=f"{config.SNAPSHOT}T00:00:00Z",
            producer=PRODUCER,
        ),
        "processingEngine": processing_engine_run.ProcessingEngineRunFacet(
            version=pd.__version__,
            name="pandas",
            producer=PRODUCER,
        ),
    }


def _file_input(
    namespace: str,
    name: str,
    description: str,
    schema_fields: list[schema_dataset.SchemaDatasetFacetFields],
    row_count: int | None,
    byte_size: int | None,
) -> InputDataset:
    facets: dict[str, Any] = {
        "datasource": datasource_dataset.DatasourceDatasetFacet(
            name=namespace, uri=namespace, producer=PRODUCER
        ),
        "documentation": documentation_dataset.DocumentationDatasetFacet(
            description=description, producer=PRODUCER
        ),
    }
    if schema_fields:
        facets["schema"] = schema_dataset.SchemaDatasetFacet(
            fields=schema_fields, producer=PRODUCER
        )
    input_facets = {}
    if row_count is not None or byte_size is not None:
        input_facets["inputStatistics"] = input_statistics_input_dataset.InputStatisticsInputDatasetFacet(
            rowCount=row_count, size=byte_size, producer=PRODUCER
        )
    return InputDataset(namespace=namespace, name=name, facets=facets, inputFacets=input_facets)


def _file_output(
    namespace: str,
    name: str,
    description: str,
    schema_fields: list[schema_dataset.SchemaDatasetFacetFields],
    row_count: int | None,
    byte_size: int | None,
    column_lineage: dict[str, list[tuple[str, str, str]]] | None = None,
) -> OutputDataset:
    """column_lineage maps output_field -> [(source_namespace, source_name, source_field), ...]."""
    facets: dict[str, Any] = {
        "datasource": datasource_dataset.DatasourceDatasetFacet(
            name=namespace, uri=namespace, producer=PRODUCER
        ),
        "documentation": documentation_dataset.DocumentationDatasetFacet(
            description=description, producer=PRODUCER
        ),
    }
    if schema_fields:
        facets["schema"] = schema_dataset.SchemaDatasetFacet(
            fields=schema_fields, producer=PRODUCER
        )
    if column_lineage:
        cl_fields = {}
        for out_field, sources in column_lineage.items():
            cl_fields[out_field] = column_lineage_dataset.Fields(
                inputFields=[
                    column_lineage_dataset.InputField(namespace=ns, name=nm, field=fld)
                    for ns, nm, fld in sources
                ],
                transformationDescription="Phase 1a clean + enrich",
                transformationType="DIRECT",
            )
        facets["columnLineage"] = column_lineage_dataset.ColumnLineageDatasetFacet(
            fields=cl_fields, producer=PRODUCER
        )
    output_facets = {}
    if row_count is not None or byte_size is not None:
        output_facets["outputStatistics"] = output_statistics_output_dataset.OutputStatisticsOutputDatasetFacet(
            rowCount=row_count, size=byte_size, producer=PRODUCER
        )
    return OutputDataset(namespace=namespace, name=name, facets=facets, outputFacets=output_facets)


# ---------------------------------------------------------------------------
# Phase definitions — input/output datasets per Phase
# ---------------------------------------------------------------------------


def _build_phase_1a_event(run_id: str, state: RunState, event_time: str) -> RunEvent:
    """Phase 1a: 6 Bronze sources -> Gold parquet + SQLite."""
    inputs = [
        _file_input(
            NS_FILE,
            f"data/raw/dxtnavis/{config.SNAPSHOT}/Refining_ObjectID_20260412_064240.xlsx",
            "Bronze: Refining ObjectID classification (XLSX, 12,009 rows × 6 class labels). "
            "Source: DXTnavis PR #3 with negative-lookahead regex for composite nouns.",
            _xlsx_schema(config.RAW_REFINING_XLSX),
            12009,
            _file_size(config.RAW_REFINING_XLSX),
        ),
        _file_input(
            NS_FILE,
            f"data/raw/dxtnavis/{config.SNAPSHOT}/AllProperties_20260407_184650.csv",
            "Bronze: SP3D AllProperties (CSV, 12,009 rows × 136 cols). Contains "
            "raw imperial-unit string values (e.g. '284.23 lbm', '17 ft  1.48 in').",
            _csv_schema(config.RAW_ALL_PROPERTIES),
            _csv_rowcount(config.RAW_ALL_PROPERTIES),
            _file_size(config.RAW_ALL_PROPERTIES),
        ),
        _file_input(
            NS_FILE,
            f"data/raw/dxtnavis/{config.SNAPSHOT}/adjacency.csv",
            "Bronze: Producer-emitted spatial adjacency edges (110,173 rows). "
            "Replaces AABB-derived adjacency (Insight 2: 35.4% precision).",
            _csv_schema(config.RAW_ADJACENCY),
            _csv_rowcount(config.RAW_ADJACENCY),
            _file_size(config.RAW_ADJACENCY),
        ),
        _file_input(
            NS_FILE,
            f"data/raw/dxtnavis/{config.SNAPSHOT}/geometry.csv",
            "Bronze: BBox, centroid, mesh metadata per ObjectID.",
            _csv_schema(config.RAW_GEOMETRY),
            _csv_rowcount(config.RAW_GEOMETRY),
            _file_size(config.RAW_GEOMETRY),
        ),
        _file_input(
            NS_FILE,
            f"data/raw/dxtnavis/{config.SNAPSHOT}/validation.csv",
            "Bronze: Mesh quality verdicts (used to derive is_container flag).",
            _csv_schema(config.RAW_VALIDATION),
            _csv_rowcount(config.RAW_VALIDATION),
            _file_size(config.RAW_VALIDATION),
        ),
        _file_input(
            NS_FILE,
            f"data/raw/dxtnavis/{config.SNAPSHOT}/connected_groups.csv",
            "Bronze: 3,355 connected components (group_id, group_size).",
            _csv_schema(config.RAW_CONNECTED_GROUPS),
            _csv_rowcount(config.RAW_CONNECTED_GROUPS),
            _file_size(config.RAW_CONNECTED_GROUPS),
        ),
    ]

    # Column lineage: a few illustrative Gold columns and where they come from.
    column_lineage = {
        "object_id": [
            (NS_FILE, f"data/raw/dxtnavis/{config.SNAPSHOT}/AllProperties_20260407_184650.csv", "ObjectId"),
        ],
        "refined_class": [
            (NS_FILE, f"data/raw/dxtnavis/{config.SNAPSHOT}/Refining_ObjectID_20260412_064240.xlsx", "Class"),
        ],
        "is_container": [
            (NS_FILE, f"data/raw/dxtnavis/{config.SNAPSHOT}/validation.csv", "verdict"),
            (NS_FILE, f"data/raw/dxtnavis/{config.SNAPSHOT}/connected_groups.csv", "group_size"),
        ],
        "is_parent_box": [
            (NS_FILE, f"data/raw/dxtnavis/{config.SNAPSHOT}/AllProperties_20260407_184650.csv", "ParentId"),
            (NS_FILE, f"data/raw/dxtnavis/{config.SNAPSHOT}/geometry.csv", "bbox_volume"),
        ],
        "dry_weight_kg": [
            (NS_FILE, f"data/raw/dxtnavis/{config.SNAPSHOT}/AllProperties_20260407_184650.csv", "sp3d_dry_weight"),
        ],
        "centroid_x": [
            (NS_FILE, f"data/raw/dxtnavis/{config.SNAPSHOT}/geometry.csv", "centroid_x"),
        ],
    }

    outputs = [
        _file_output(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_objects_enriched.parquet",
            "Gold: 12,009 BIM objects × 219 enriched columns. Includes refined_class "
            "(7 categories), SI-unit physics columns, derived flags (is_container, "
            "is_analysis_volume, is_parent_box, graph_participant), confidence layer.",
            _parquet_schema(config.ENRICHED_OBJECTS),
            _parquet_rowcount(config.ENRICHED_OBJECTS),
            _file_size(config.ENRICHED_OBJECTS),
            column_lineage=column_lineage,
        ),
        _file_output(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_adjacency_sym.parquet",
            "Gold: Symmetric closure of producer adjacency (220,346 edges = 110,173 × 2).",
            _parquet_schema(config.ENRICHED_ADJACENCY_SYM),
            _parquet_rowcount(config.ENRICHED_ADJACENCY_SYM),
            _file_size(config.ENRICHED_ADJACENCY_SYM),
        ),
        _file_output(
            NS_SQLITE,
            "bimkg.db",
            "Gold: SQLite warehouse with bim_objects, bim_adjacency, bim_hierarchy, "
            "bim_connected_groups + FTS5 full-text index on display_name.",
            [],
            12009,
            _file_size(config.SQLITE_BIMKG),
        ),
    ]

    return RunEvent(
        eventType=state,
        eventTime=event_time,
        run=Run(runId=run_id, facets=_run_facets()),
        job=Job(
            namespace="bimkg",
            name="phase_1a_silver_gold",
            facets=_job_facets(
                description="Phase 1a: Bronze -> Silver -> Gold. XLSX classifier + unit "
                "conversion + column rename + derived flags + confidence layer.",
                source_path="src/bimkg/ingest/sqlite_writer.py",
            ),
        ),
        producer=PRODUCER,
        inputs=inputs,
        outputs=outputs,
    )


def _build_phase_1d_powerbi_event(run_id: str, state: RunState, event_time: str) -> RunEvent:
    inputs = [
        _file_input(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_objects_enriched.parquet",
            "Gold: enriched BIM objects (219 cols).",
            _parquet_schema(config.ENRICHED_OBJECTS),
            _parquet_rowcount(config.ENRICHED_OBJECTS),
            _file_size(config.ENRICHED_OBJECTS),
        ),
    ]
    outputs = [
        _file_output(
            NS_FILE,
            f"data/powerbi/{config.SNAPSHOT}/",
            "Power BI star schema: 10 CSV files (dim_class, dim_pipeline, dim_level, "
            "fact_objects, fact_adjacency, etc.).",
            [],
            None,
            None,
        ),
    ]
    return RunEvent(
        eventType=state,
        eventTime=event_time,
        run=Run(runId=run_id, facets=_run_facets()),
        job=Job(
            namespace="bimkg",
            name="phase_1d_powerbi_export",
            facets=_job_facets(
                description="Phase 1d: Gold -> Power BI 10-CSV star schema",
                source_path="src/bimkg/ingest/exporters/powerbi.py",
            ),
        ),
        producer=PRODUCER,
        inputs=inputs,
        outputs=outputs,
    )


def _build_phase_1d_foundry_event(run_id: str, state: RunState, event_time: str) -> RunEvent:
    """Phase 1d Foundry: maps to 10 Foundry datasets via palantir:// namespace."""
    foundry_datasets = [
        ("bim_piping", "PipingComponent rows", "ri.foundry.main.dataset.2388ddc2-3c83-4ef3-a7df-fef11024bb4e"),
        ("bim_structural", "StructuralMember rows", "ri.foundry.main.dataset.32658e86-ad1b-4adb-8acf-c3c409a21661"),
        ("bim_equipment", "Equipment rows", "ri.foundry.main.dataset.5e250030-37c1-4475-aaac-8a9e9bf42e64"),
        ("bim_electrical", "ElectricalComponent rows", "ri.foundry.main.dataset.29338c90-e5be-4db7-86f9-eb0449340873"),
        ("bim_hvac", "HvacComponent rows", "ri.foundry.main.dataset.914af224-32c8-48c5-b419-47eab341e33b"),
        ("bim_other", "UncategorizedObject rows", "ri.foundry.main.dataset.87c921ea-cfcb-4ba5-b656-4bcacde11804"),
        ("bim_adjacent_to", "AdjacentTo link rows", "ri.foundry.main.dataset.d6f789d4-54d7-49d1-9351-b20e825624dc"),
        ("bim_has_parent", "HasParent link rows", "ri.foundry.main.dataset.159d949e-fe9b-4267-a20e-57512e0600d8"),
        ("bim_belongs_to_pipeline", "BelongsToPipeline link rows", "ri.foundry.main.dataset.97db7363-a24e-4cd8-870c-39450ba9bbfa"),
        ("bim_in_group", "InGroup link rows", "ri.foundry.main.dataset.0e57446a-bbc6-4443-bec8-7cbf58103e65"),
    ]
    inputs = [
        _file_input(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_objects_enriched.parquet",
            "Gold: enriched BIM objects (219 cols).",
            _parquet_schema(config.ENRICHED_OBJECTS),
            _parquet_rowcount(config.ENRICHED_OBJECTS),
            _file_size(config.ENRICHED_OBJECTS),
        ),
        _file_input(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_adjacency_sym.parquet",
            "Gold: Symmetric adjacency.",
            _parquet_schema(config.ENRICHED_ADJACENCY_SYM),
            _parquet_rowcount(config.ENRICHED_ADJACENCY_SYM),
            _file_size(config.ENRICHED_ADJACENCY_SYM),
        ),
    ]
    outputs = [
        _file_output(
            NS_FOUNDRY,
            f"/Datayoon-09825c/BIM-KG/{name}",
            f"Foundry dataset: {desc}. RID: {rid}",
            [],
            None,
            None,
        )
        for name, desc, rid in foundry_datasets
    ]
    return RunEvent(
        eventType=state,
        eventTime=event_time,
        run=Run(runId=run_id, facets=_run_facets()),
        job=Job(
            namespace="bimkg",
            name="phase_1d_foundry_export",
            facets=_job_facets(
                description="Phase 1d: Gold -> 10 Foundry datasets via palantir-sdk. "
                "6 ObjectType-backing tables + 4 LinkType-backing tables.",
                source_path="src/bimkg/ingest/exporters/foundry_upload.py",
            ),
        ),
        producer=PRODUCER,
        inputs=inputs,
        outputs=outputs,
    )


def _build_phase_2_tbox_event(run_id: str, state: RunState, event_time: str) -> RunEvent:
    outputs = [
        _file_output(
            NS_FILE,
            f"data/ontology/{config.SNAPSHOT}/owl/bim-ontology.owl",
            "OWL TBox: BIMObject hierarchy (PhysicalObject, Container, AnalysisVolume), "
            "object properties (adjacentTo symmetric, belongsToPipeline, hasParent), "
            "data properties (objectId, dryWeight, centroid_x/y/z, etc.).",
            [],
            None,
            _file_size(config.ONTOLOGY_OWL),
        ),
    ]
    return RunEvent(
        eventType=state,
        eventTime=event_time,
        run=Run(runId=run_id, facets=_run_facets()),
        job=Job(
            namespace="bimkg",
            name="phase_2_owl_tbox",
            facets=_job_facets(
                description="Phase 2: Generate OWL TBox (class hierarchy + properties)",
                source_path="src/bimkg/ontology/schema.py",
            ),
        ),
        producer=PRODUCER,
        inputs=[],
        outputs=outputs,
    )


def _build_phase_2_abox_event(run_id: str, state: RunState, event_time: str) -> RunEvent:
    inputs = [
        _file_input(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_objects_enriched.parquet",
            "Gold: enriched BIM objects (219 cols).",
            _parquet_schema(config.ENRICHED_OBJECTS),
            _parquet_rowcount(config.ENRICHED_OBJECTS),
            _file_size(config.ENRICHED_OBJECTS),
        ),
        _file_input(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_adjacency_sym.parquet",
            "Gold: Symmetric adjacency.",
            _parquet_schema(config.ENRICHED_ADJACENCY_SYM),
            _parquet_rowcount(config.ENRICHED_ADJACENCY_SYM),
            _file_size(config.ENRICHED_ADJACENCY_SYM),
        ),
        _file_input(
            NS_FILE,
            f"data/ontology/{config.SNAPSHOT}/owl/bim-ontology.owl",
            "OWL TBox.",
            [],
            None,
            _file_size(config.ONTOLOGY_OWL),
        ),
    ]
    outputs = [
        _file_output(
            NS_FILE,
            f"data/ontology/{config.SNAPSHOT}/owl/bim-objects.ttl",
            "OWL ABox: ~477K triples across 3 TTL files (objects, adjacency, hierarchy).",
            [],
            None,
            _file_size(config.ONTOLOGY_INSTANCES),
        ),
    ]
    return RunEvent(
        eventType=state,
        eventTime=event_time,
        run=Run(runId=run_id, facets=_run_facets()),
        job=Job(
            namespace="bimkg",
            name="phase_2_owl_abox",
            facets=_job_facets(
                description="Phase 2: Generate OWL ABox instances (12K objects, 220K spatial triples)",
                source_path="src/bimkg/ontology/instances.py",
            ),
        ),
        producer=PRODUCER,
        inputs=inputs,
        outputs=outputs,
    )


def _build_phase_3_shacl_event(run_id: str, state: RunState, event_time: str) -> RunEvent:
    outputs = [
        _file_output(
            NS_FILE,
            f"data/ontology/{config.SNAPSHOT}/owl/bim-shapes.ttl",
            "SHACL shapes: 6 NodeShapes (PipingMustHavePipeline, EquipmentMustHaveName, "
            "PhysicalObjectMustHaveMesh, PipingLevelGuard, NoAnalysisVolumeInGraph, "
            "WeightNonNegative).",
            [],
            None,
            _file_size(config.ONTOLOGY_SHAPES),
        ),
    ]
    return RunEvent(
        eventType=state,
        eventTime=event_time,
        run=Run(runId=run_id, facets=_run_facets()),
        job=Job(
            namespace="bimkg",
            name="phase_3_shacl_shapes",
            facets=_job_facets(
                description="Phase 3: Generate SHACL shapes for data quality validation",
                source_path="src/bimkg/validation/shapes.py",
            ),
        ),
        producer=PRODUCER,
        inputs=[],
        outputs=outputs,
    )


def _build_phase_4_neo4j_event(run_id: str, state: RunState, event_time: str) -> RunEvent:
    inputs = [
        _file_input(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_objects_enriched.parquet",
            "Gold: enriched BIM objects (219 cols).",
            _parquet_schema(config.ENRICHED_OBJECTS),
            _parquet_rowcount(config.ENRICHED_OBJECTS),
            _file_size(config.ENRICHED_OBJECTS),
        ),
        _file_input(
            NS_FILE,
            f"data/enriched/{config.SNAPSHOT}/bim_adjacency_sym.parquet",
            "Gold: Symmetric adjacency.",
            _parquet_schema(config.ENRICHED_ADJACENCY_SYM),
            _parquet_rowcount(config.ENRICHED_ADJACENCY_SYM),
            _file_size(config.ENRICHED_ADJACENCY_SYM),
        ),
    ]
    outputs = [
        _file_output(
            NS_FILE,
            f"data/ontology/{config.SNAPSHOT}/neo4j/",
            "Neo4j CSV bundle: 261K edges across 6 relationship types (ADJACENT_TO, "
            "PRECEDES, BELONGS_TO_PIPELINE, HAS_PARENT, IN_ZONE, IN_GROUP) + nodes.",
            [],
            None,
            None,
        ),
    ]
    return RunEvent(
        eventType=state,
        eventTime=event_time,
        run=Run(runId=run_id, facets=_run_facets()),
        job=Job(
            namespace="bimkg",
            name="phase_4_neo4j_export",
            facets=_job_facets(
                description="Phase 4: Build physical graph + Louvain zones + precedence DAG -> Neo4j CSV",
                source_path="src/bimkg/analytics/neo4j_export.py",
            ),
        ),
        producer=PRODUCER,
        inputs=inputs,
        outputs=outputs,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


PHASE_BUILDERS = [
    ("phase_1a_silver_gold", _build_phase_1a_event),
    ("phase_1d_powerbi_export", _build_phase_1d_powerbi_event),
    ("phase_1d_foundry_export", _build_phase_1d_foundry_event),
    ("phase_2_owl_tbox", _build_phase_2_tbox_event),
    ("phase_2_owl_abox", _build_phase_2_abox_event),
    ("phase_3_shacl_shapes", _build_phase_3_shacl_event),
    ("phase_4_neo4j_export", _build_phase_4_neo4j_event),
]


def emit_pipeline_events(output_dir: Path | None = None) -> tuple[Path, Path]:
    """Emit START + COMPLETE events for every Phase, write JSONL + summary.

    Returns (events_path, summary_path).
    """
    output_dir = output_dir or (config.DATA_ROOT / "lineage" / config.SNAPSHOT)
    output_dir.mkdir(parents=True, exist_ok=True)
    events_path = output_dir / "openlineage-events.jsonl"
    summary_path = output_dir / "openlineage-summary.json"

    events: list[RunEvent] = []
    for _job_name, builder in PHASE_BUILDERS:
        run_id = str(uuid.uuid4())
        start_t = _utcnow()
        events.append(builder(run_id, RunState.START, start_t))
        events.append(builder(run_id, RunState.COMPLETE, _utcnow()))

    with events_path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(Serde.to_json(ev) + "\n")

    summary = {
        "snapshot": config.SNAPSHOT,
        "producer": PRODUCER,
        "git_revision": _git_rev(),
        "generated_at": _utcnow(),
        "event_count": len(events),
        "jobs": [
            {
                "name": name,
                "input_count": sum(1 for _ in (builder(str(uuid.uuid4()), RunState.START, _utcnow()).inputs or [])),
                "output_count": sum(1 for _ in (builder(str(uuid.uuid4()), RunState.START, _utcnow()).outputs or [])),
            }
            for name, builder in PHASE_BUILDERS
        ],
        "namespaces_used": [NS_FILE, NS_SQLITE, NS_FOUNDRY],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return events_path, summary_path
