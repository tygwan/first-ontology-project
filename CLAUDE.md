# Project: first-ontology-project

> Runtime activation point for dev-standards rules in Claude Code sessions.

---

## Dev standards version

- **Source**: https://github.com/tygwan/dev-standards
- **Version pinned**: `0.3.0`
- **Rules applied**: R1-R11 (see source for details)
- **Consumer role**: 🟢 First consumer / reference implementation

## Active memory rules

Claude Code memory files in `~/.claude/projects/.../memory/` apply the
following rules at session start:

- `feedback_task_logging.md` — R2 (5-section task log in `docs/tasklog/`)
- `feedback_finding_archive.md` — R3 (6-step issue archive in `docs/findings/`)

Historical note: The `portal update` rule (R1/R4) is currently integrated
into `feedback_finding_archive.md` step 5 in this project's memory. The
separately-named `feedback_portal_update.md` file lives in the
`dev-standards` repo and may be added here in a future session.

## Project-specific context

- **Goal**: BIM ontology / knowledge graph pipeline for SP3D plant model data (12,009 objects × 110,173 spatial relations)
- **Upstream data**: DXTnavis v1.4.0 snapshot `2026-04-12` (PR #3 XLSX fix re-aligned)
- **Current phase**: Phase 0–6 complete; Foundry 6 ObjectTypes live; Airflow DAG + OpenLineage live. Phase 7 (Streamlit UI) pending.
- **Primary targets**: Palantir Foundry (Developer Tier) + Power BI + Neo4j + FastAPI + LLM Agent
- **Test suite**: 336/336 passing

## Conventions this project follows

- **R1 Directory layout**: `docs/{plan,analysis,tasklog,findings,reference}/`
- **R1 Single portal**: `docs/PROJECT-JOURNAL.md`
- **R2 Task logging**: 5-section format in `docs/tasklog/phase-*.md`
- **R3 Finding archival**: 6-step process in `docs/findings/YYYY-MM-DD-ID-slug/`
- **R4 Decision records**: `PROJECT-JOURNAL.md §4` with IDs D1-D9+
- **R5 Git workflow**: atomic commits, imperative titles, commit+push pair
- **R6 External dependencies**: `PROJECT-JOURNAL.md §5` (DXTnavis tracked)
- **R7 Issue severity**: CRITICAL/MAJOR/MINOR + Open/Fixing/Resolved/Deferred/Accepted
- **R8 Human-AI collab**: explicit trade-off analysis + escalation on structural decisions
- **R9 Provenance**: `SNAPSHOT = "2026-04-12"` pinned + lineage columns + audit scripts
- **R10 Decision validation**: A/B comparisons documented (e.g., AABB vs Producer adjacency)
- **R11 Portfolio writing** (🟢 MAY): `portfolio/architecture-diagrams.html` + future portfolio MD must follow PAAR + 2-part narrative + Visual Asset Checklist

## Quick commands

```bash
# Environment
uv pip install -e ".[dev]"

# Test
make test
.venv/bin/python -m pytest

# Phase 1 verification snapshot
.venv/bin/python scripts/verify_phase1.py
```

## Related

- **Standards**: [dev-standards@0.3.0](https://github.com/tygwan/dev-standards)
- **Project portal**: [`docs/PROJECT-JOURNAL.md`](docs/PROJECT-JOURNAL.md) ← 단일 내비게이션
- **First consumer example**: [`dev-standards/examples/first-ontology-project.md`](https://github.com/tygwan/dev-standards/blob/main/examples/first-ontology-project.md)
