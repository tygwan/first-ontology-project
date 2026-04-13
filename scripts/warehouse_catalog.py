"""DBA-perspective warehouse catalog for the BIM SQLite warehouse.

Generates a metadata catalog covering:

- Schemas:        all tables + columns + types + nullability + PK
- Statistics:     row counts, null counts per column, distinct value counts
- Indexes:        existing indexes + recommended indexes (based on usage)
- Foreign-key relationships (logical, since SQLite doesn't enforce by default)
- Storage:        page size, file size, freelist
- Sample queries: idiomatic SELECTs per table

Output:
    docs/reference/warehouse-catalog/{SNAPSHOT}/catalog.md       — human-readable
    docs/reference/warehouse-catalog/{SNAPSHOT}/catalog.json     — machine-readable

Usage:
    .venv/bin/python scripts/warehouse_catalog.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bimkg import config

# Logical FK relationships (SQLite doesn't store these; we declare them).
LOGICAL_FKS = [
    ("bim_adjacency", "source_object_id", "bim_objects", "object_id"),
    ("bim_adjacency", "target_object_id", "bim_objects", "object_id"),
]

# Recommended indexes (based on common query patterns observed in src/bimkg/).
RECOMMENDED_INDEXES = [
    ("bim_objects", "refined_class", "Filter by classification"),
    ("bim_objects", "pipeline", "Group/filter by pipeline (157 distinct)"),
    ("bim_objects", "level", "Filter by floor level"),
    ("bim_objects", "is_container", "Hide container parents from analytics"),
    ("bim_objects", "is_analysis_volume", "Hide analysis volumes from graph"),
    ("bim_adjacency", "source_object_id", "Outgoing edge lookup (FK join)"),
    ("bim_adjacency", "target_object_id", "Incoming edge lookup (FK join)"),
]


def _table_columns(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [
        {
            "ordinal": r[0],
            "name": r[1],
            "type": r[2],
            "notnull": bool(r[3]),
            "default": r[4],
            "pk": bool(r[5]),
        }
        for r in rows
    ]


def _table_row_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _column_stats(conn: sqlite3.Connection, table: str, columns: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """For each non-text column with reasonable cardinality, compute null + distinct counts."""
    stats: dict[str, dict[str, int]] = {}
    total = _table_row_count(conn, table)
    for col in columns:
        name = col["name"]
        # Skip extremely wide string columns to keep this fast
        try:
            null_count = conn.execute(
                f'SELECT COUNT(*) FROM {table} WHERE "{name}" IS NULL'
            ).fetchone()[0]
            distinct_count = conn.execute(
                f'SELECT COUNT(DISTINCT "{name}") FROM {table}'
            ).fetchone()[0]
            stats[name] = {
                "null_count": null_count,
                "null_pct": round(100 * null_count / total, 2) if total else 0,
                "distinct_count": distinct_count,
                "distinct_pct": round(100 * distinct_count / total, 2) if total else 0,
            }
        except sqlite3.OperationalError:
            # FTS shadow tables don't support arbitrary queries
            stats[name] = {"null_count": -1, "distinct_count": -1}
    return stats


def _existing_indexes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT name, tbl_name, sql FROM sqlite_master "
        "WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [{"name": r[0], "table": r[1], "sql": r[2]} for r in rows]


def _storage_info(conn: sqlite3.Connection, db_path: Path) -> dict[str, Any]:
    return {
        "file_size_bytes": db_path.stat().st_size,
        "page_size": conn.execute("PRAGMA page_size").fetchone()[0],
        "page_count": conn.execute("PRAGMA page_count").fetchone()[0],
        "freelist_count": conn.execute("PRAGMA freelist_count").fetchone()[0],
        "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
        "auto_vacuum": conn.execute("PRAGMA auto_vacuum").fetchone()[0],
        "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
        "encoding": conn.execute("PRAGMA encoding").fetchone()[0],
    }


def _sample_queries(table: str) -> list[str]:
    if table == "bim_objects":
        return [
            "SELECT refined_class, COUNT(*) FROM bim_objects GROUP BY refined_class ORDER BY 2 DESC;",
            "SELECT * FROM bim_objects WHERE pipeline = 'P-10147' AND is_container = 0;",
            "SELECT pipeline, COUNT(*) AS objects, SUM(dry_weight_kg) AS total_kg "
            "  FROM bim_objects WHERE refined_class='PipingComponent' "
            "  GROUP BY pipeline ORDER BY total_kg DESC LIMIT 20;",
        ]
    if table == "bim_adjacency":
        return [
            "SELECT source_object_id, COUNT(*) AS degree FROM bim_adjacency "
            "  GROUP BY source_object_id ORDER BY degree DESC LIMIT 10;",
            "SELECT relation_type, COUNT(*) FROM bim_adjacency GROUP BY relation_type;",
        ]
    if table == "bim_objects_fts":
        return [
            "SELECT object_id, display_name FROM bim_objects_fts "
            "  WHERE bim_objects_fts MATCH 'pump' LIMIT 20;",
        ]
    return []


def build_catalog(db_path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    table_names = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]

    tables_meta = []
    for tbl in table_names:
        cols = _table_columns(conn, tbl)
        # Only run column stats on physical (non-FTS-shadow) tables
        is_fts_shadow = tbl.endswith(("_data", "_idx", "_docsize", "_config"))
        stats = {} if is_fts_shadow else _column_stats(conn, tbl, cols)
        tables_meta.append(
            {
                "name": tbl,
                "row_count": _table_row_count(conn, tbl),
                "column_count": len(cols),
                "is_fts_shadow": is_fts_shadow,
                "columns": cols,
                "column_stats": stats,
                "sample_queries": _sample_queries(tbl),
            }
        )

    return {
        "snapshot": config.SNAPSHOT,
        "database": str(db_path.relative_to(PROJECT_ROOT)),
        "storage": _storage_info(conn, db_path),
        "tables": tables_meta,
        "indexes_existing": _existing_indexes(conn),
        "indexes_recommended": [
            {"table": t, "column": c, "rationale": r} for t, c, r in RECOMMENDED_INDEXES
        ],
        "logical_foreign_keys": [
            {"from_table": ft, "from_column": fc, "to_table": tt, "to_column": tc}
            for ft, fc, tt, tc in LOGICAL_FKS
        ],
    }


def _md_table_section(tbl: dict[str, Any]) -> str:
    lines = []
    lines.append(f"### `{tbl['name']}`\n")
    lines.append(f"- **Rows**: {tbl['row_count']:,}")
    lines.append(f"- **Columns**: {tbl['column_count']}")
    if tbl["is_fts_shadow"]:
        lines.append("- **Type**: FTS5 shadow table (do not query directly)\n")
        return "\n".join(lines)
    lines.append("")

    lines.append("| # | Column | Type | NotNull | PK | Null % | Distinct % |")
    lines.append("|---|--------|------|:-------:|:--:|-------:|-----------:|")
    for col in tbl["columns"][:30]:  # truncate wide tables in markdown
        s = tbl["column_stats"].get(col["name"], {})
        null_pct = s.get("null_pct", "-")
        dist_pct = s.get("distinct_pct", "-")
        lines.append(
            f"| {col['ordinal']} | `{col['name']}` | {col['type'] or '?'} | "
            f"{'Y' if col['notnull'] else ''} | {'Y' if col['pk'] else ''} | "
            f"{null_pct} | {dist_pct} |"
        )
    if len(tbl["columns"]) > 30:
        lines.append(f"\n_Showing first 30 of {tbl['column_count']} columns. See JSON catalog for full list._")
    if tbl["sample_queries"]:
        lines.append("\n**Sample queries**:")
        for q in tbl["sample_queries"]:
            lines.append(f"\n```sql\n{q}\n```")
    return "\n".join(lines)


def write_markdown(catalog: dict[str, Any], out_path: Path) -> None:
    lines = []
    lines.append(f"# Warehouse Catalog — {catalog['snapshot']}\n")
    lines.append(f"> Generated by `scripts/warehouse_catalog.py`. Do not edit by hand.\n")
    lines.append(f"**Database**: `{catalog['database']}`\n")

    s = catalog["storage"]
    lines.append("## Storage\n")
    lines.append("| Property | Value |")
    lines.append("|----------|-------|")
    lines.append(f"| File size | {s['file_size_bytes']:,} bytes ({s['file_size_bytes']/1_048_576:.1f} MB) |")
    lines.append(f"| Page size | {s['page_size']:,} bytes |")
    lines.append(f"| Page count | {s['page_count']:,} |")
    lines.append(f"| Freelist count | {s['freelist_count']:,} |")
    lines.append(f"| Journal mode | `{s['journal_mode']}` |")
    lines.append(f"| Auto vacuum | {s['auto_vacuum']} |")
    lines.append(f"| User version | {s['user_version']} |")
    lines.append(f"| Encoding | `{s['encoding']}` |")

    lines.append("\n## Tables\n")
    for tbl in catalog["tables"]:
        lines.append(_md_table_section(tbl))
        lines.append("")

    lines.append("## Existing Indexes\n")
    if catalog["indexes_existing"]:
        for idx in catalog["indexes_existing"]:
            lines.append(f"- `{idx['name']}` on `{idx['table']}` — `{idx['sql']}`")
    else:
        lines.append("_None._\n")

    lines.append("\n## Recommended Indexes\n")
    lines.append("| Table | Column | Rationale |")
    lines.append("|-------|--------|-----------|")
    for idx in catalog["indexes_recommended"]:
        lines.append(f"| `{idx['table']}` | `{idx['column']}` | {idx['rationale']} |")

    lines.append("\n## Logical Foreign Keys\n")
    lines.append("> SQLite does not enforce these; declared here for documentation.\n")
    lines.append("| From | To |")
    lines.append("|------|-----|")
    for fk in catalog["logical_foreign_keys"]:
        lines.append(
            f"| `{fk['from_table']}.{fk['from_column']}` | "
            f"`{fk['to_table']}.{fk['to_column']}` |"
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    db_path = config.SQLITE_BIMKG
    if not db_path.exists():
        print(f"[!] Warehouse not found at {db_path}")
        return 1

    out_dir = PROJECT_ROOT / "docs" / "reference" / "warehouse-catalog" / config.SNAPSHOT
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog = build_catalog(db_path)

    json_path = out_dir / "catalog.json"
    md_path = out_dir / "catalog.md"
    json_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    write_markdown(catalog, md_path)

    print(f"[OK] {json_path}  ({json_path.stat().st_size:,} bytes)")
    print(f"[OK] {md_path}    ({md_path.stat().st_size:,} bytes)")
    print(f"[OK] {len(catalog['tables'])} tables cataloged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
