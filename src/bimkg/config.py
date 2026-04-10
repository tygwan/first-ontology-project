"""Project-wide paths and constants.

All paths resolve from the project root, which is 2 levels above this file
(src/bimkg/config.py -> src/bimkg -> src -> project root).
"""

from pathlib import Path

# Project root
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# Data directories
DATA_ROOT: Path = PROJECT_ROOT / "data"
DATA_RAW_ROOT: Path = DATA_ROOT / "raw"
DATA_WORKING_ROOT: Path = DATA_ROOT / "working"
DATA_POWERBI_ROOT: Path = DATA_ROOT / "powerbi"
DATA_ONTOLOGY_ROOT: Path = DATA_ROOT / "ontology"

# The single authoritative snapshot
SNAPSHOT: str = "2026-04-07"
DATA_RAW: Path = DATA_RAW_ROOT / "dxtnavis" / SNAPSHOT
POWERBI_DIR: Path = DATA_POWERBI_ROOT / SNAPSHOT

# Raw source files
RAW_ALL_PROPERTIES: Path = DATA_RAW / "AllProperties_20260407_184650.csv"
RAW_ADJACENCY: Path = DATA_RAW / "adjacency.csv"
RAW_GEOMETRY: Path = DATA_RAW / "geometry.csv"
RAW_VALIDATION: Path = DATA_RAW / "validation.csv"
RAW_CONNECTED_GROUPS: Path = DATA_RAW / "connected_groups.csv"
RAW_TESSELLATION_FAILURES: Path = DATA_RAW / "tessellation_failures.csv"
RAW_MANIFEST: Path = DATA_RAW / "manifest.json"

# Existing semantic SQLite (read-only during Phase 1;
# new tables will be added by sqlite_enrich.py)
SQLITE_DB: Path = DATA_WORKING_ROOT / "dxtnavis" / "dxtnavis-semantic.db"

# Phase 1 outputs
SQLITE_BIMKG: Path = DATA_WORKING_ROOT / "dxtnavis" / "bimkg.db"

# Phase 2+ outputs
ONTOLOGY_OWL: Path = DATA_ONTOLOGY_ROOT / "bim-ontology.owl"
ONTOLOGY_INSTANCES: Path = DATA_ONTOLOGY_ROOT / "bim-instances.ttl"
ONTOLOGY_SHAPES: Path = DATA_ONTOLOGY_ROOT / "bim-shapes.ttl"
ONTOLOGY_INFERRED: Path = DATA_ONTOLOGY_ROOT / "bim-inferred.ttl"

# Expected counts from the 2026-04-07 snapshot (used in tests)
EXPECTED_OBJECT_COUNT: int = 12009
EXPECTED_ADJACENCY_COUNT: int = 110173
EXPECTED_CONNECTED_GROUPS: int = 3355
EXPECTED_GIANT_GROUP_SIZE: int = 8626
EXPECTED_PIPELINE_COUNT: int = 157
