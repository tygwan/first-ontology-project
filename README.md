# Ontology for Construction Management

> SP3D 기반 플랜트 BIM 모델(12,009 객체 × 220K 공간 관계)을
> **온톨로지 기반 지식 그래프**로 변환하여 시공 순서 분석·품질 검증·
> 자연어 질의가 가능한 파이프라인을 Python 단일 저장소로 제공합니다.

**Pipeline**: `BIM → Ingest → OWL Ontology → Graph Analytics → Neo4j / LLM / API`

**Data**: [DXTnavis](https://github.com/tygwan/DXTnavis) v1.4.0 snapshot `2026-04-12`
**Target platform**: Palantir Foundry (Developer Tier) + Neo4j + Power BI
**Tests**: 336 passing | **OWL triples**: 477K | **Neo4j edges**: 261K | **Foundry**: 10 datasets uploaded

## Quick Start

```bash
# Python 3.12 + uv
uv venv --python 3.12
uv pip install -e ".[dev]"

# Run tests (290 tests, ~2.5 min)
pytest

# Phase 1 pipeline (Bronze → Silver → Gold → PowerBI → Foundry)
python -c "from bimkg.ingest.sqlite_writer import run_phase_1a; run_phase_1a()"
python -c "from bimkg.ingest.exporters.powerbi import run_powerbi_export; run_powerbi_export()"
python -c "from bimkg.ingest.exporters.foundry import run_foundry_export; run_foundry_export()"

# Phase 2 ontology (OWL TBox + ABox)
python -c "from bimkg.ontology.schema import generate_tbox; generate_tbox()"
python -c "from bimkg.ontology.instances import generate_abox; generate_abox()"

# Neo4j (Docker)
docker run -d --name bimkg-neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bimkg2026 \
  -v "$(realpath data/ontology/2026-04-12/neo4j)":/import \
  neo4j:5-community
# → http://localhost:7474
```

## Notebooks

GitHub 에서 시각화 포함 렌더링됩니다:

| Notebook | 내용 |
|----------|------|
| [`01_eda.ipynb`](notebooks/01_eda.ipynb) | 컬럼 품질, 클래스 비교, 3D 공간 분포, 파이프라인 구조, 그래프 허브, 품질 의심 |
| [`02_construction_management.ipynb`](notebooks/02_construction_management.ipynb) | 양중 지도, 시공 존 A/B 테스트 (Grid vs Louvain), 파이프라인 교차, 존 내 설치 순서 |
| [`03_adjacency_tiers.ipynb`](notebooks/03_adjacency_tiers.ipynb) | Adjacency AABB 근거 분석, 3단계 분류 (Strong/Medium/Weak), Critical chain A/B (88→17 steps), Neo4j Cypher 참조 |

## Documentation

- **[Project Journal](docs/PROJECT-JOURNAL.md)** — 단일 포털: 문제·결정·타임라인 내비게이션
- **[Implementation Plan](docs/plan/pipeline-implementation-plan.md)** — 7단계 파이프라인 계획
- **[Findings Archive](docs/findings/)** — 데이터 이슈 아카이브 (M1: classification, M2: adjacency tiers)
- **[Task Logs](docs/tasklog/)** — 단계별 작업 기록

<details>
<summary><b>Project Structure</b></summary>

```
first-ontology-project/
├── src/bimkg/
│   ├── config.py                 # 경로 상수, SNAPSHOT, expected counts
│   ├── ingest/                   # Phase 1 — Bronze → Silver → Gold
│   │   ├── xlsx_classifier.py    # C# InferClass Python 포트 (negative lookahead)
│   │   ├── xlsx_loader.py        # XLSX → snake_case DataFrame
│   │   ├── clean.py              # Silver + Gold builder + confidence layer
│   │   ├── unit_parser.py        # SP3D 문자열 → SI 단위
│   │   ├── sqlite_writer.py      # Parquet + SQLite 출력
│   │   └── exporters/            # PowerBI CSV + Foundry Parquet
│   ├── ontology/                 # Phase 2 — OWL TBox + ABox
│   │   ├── namespaces.py         # BIM, INST, SPATIAL namespace 정의
│   │   ├── schema.py             # 28 OWL classes + 40 properties → bim-ontology.owl
│   │   └── instances.py          # 12K objects + 220K spatial → 3 TTL files
│   ├── analytics/                # Phase 4 — Graph analytics + KPIs
│   │   ├── metrics.py            # Degree centrality, clustering
│   │   ├── zones.py              # Louvain community (tunable resolution)
│   │   ├── precedence.py         # Construction precedence DAG + adjacency_tier
│   │   ├── kpi.py                # 33 KPIs (criticality, accessibility, corrosion)
│   │   └── neo4j_export.py       # Neo4j CSV (nodes + 6 edge types)
│   ├── llm/                      # Phase 5 — LLM/GraphRAG
│   │   ├── tools.py              # 5 retrieval tools (SQL, FTS5, SPARQL, Cypher, KPI)
│   │   ├── agent.py              # LangGraph ReAct agent (Gemini/Claude)
│   │   └── prompts.py            # System prompt + few-shot examples
│   └── api/                      # Phase 6 — FastAPI backend
│       └── main.py               # 12 REST endpoints
│
├── tests/                        # 336 tests (+2 E2E skipped)
│   ├── test_ingest/              # 212 tests
│   ├── test_ontology/            # 59 tests
│   ├── test_analytics/           # 19 tests
│   ├── test_validation/          # 14 tests
│   ├── test_llm/                 # 19 tests (17 + 2 E2E)
│   └── test_api/                 # 14 tests
│
├── notebooks/                    # EDA + CM analysis + A/B tests
│
├── data/                         # gitignored — Medallion architecture
│   ├── raw/dxtnavis/2026-04-12/  # Bronze (11 files, read-only)
│   ├── clean/2026-04-12/         # Silver (4 parquet)
│   ├── enriched/2026-04-12/      # Gold (218 cols parquet + SQLite)
│   ├── ontology/2026-04-12/      # Object/Link Types + OWL + Neo4j CSV
│   └── powerbi/2026-04-12/       # 10 CSV star schema
│
└── docs/
    ├── PROJECT-JOURNAL.md        # 단일 포털
    ├── findings/                 # M1 (classification), M2 (adjacency tiers)
    ├── tasklog/                  # Phase 별 5-section 작업 기록
    └── analysis/                 # 설계 결정 문서
```

</details>

<details>
<summary><b>Current Status</b></summary>

| Phase | 상태 | 테스트 | 핵심 산출물 |
|-------|------|------:|-----------|
| 0. Bootstrap | ✅ | 3 | pyproject.toml, config.py |
| 1a~1e. Ingest | ✅ | 212 | Gold 219 cols, SQLite, oracle 100%, confidence |
| 2. OWL Ontology | ✅ | 59 | TBox (28 classes) + ABox (477K triples) |
| 3. SHACL Validation | ✅ | 14 | 6 shapes, 468 violations |
| 4. Graph Analytics | ✅ | 19 | Precedence DAG, 33 KPIs, Neo4j 261K edges |
| 5. LLM/GraphRAG | ✅ | 19 | 5 tools, Gemini 2.5 Flash agent |
| 6. FastAPI | ✅ | 14 | 12 REST endpoints |
| Foundry | ✅ | — | 10 datasets uploaded to BIM-KG project |
| 7. Streamlit UI | ⏸ | — | — |

**Total**: 336 tests passing (+2 E2E skipped)

</details>

<details>
<summary><b>OWL Ontology (Phase 2)</b></summary>

### Class Hierarchy (D10: sibling structure)

```
BIMEntity
├── BIMObject
│   ├── PhysicalObject
│   │   ├── PipingComponent (2,841)
│   │   ├── StructuralMember (2,659)
│   │   ├── Equipment → 8 subclasses from Eqp Type 0 (715)
│   │   ├── ElectricalComponent (886)
│   │   ├── HvacComponent (68)
│   │   └── UncategorizedObject (1,342)
│   └── Container
│       └── HierarchyNode (3,353)
└── AnalysisArtifact
    └── AnalysisVolume (145)
```

### ABox Files (Q6: concern-based split)

| File | Size | Content |
|------|-----:|---------|
| `bim-ontology.owl` | 9 KB | TBox — 28 classes, 8 object props, 32 data props |
| `bim-shared.ttl` | 0.1 MB | 505 named individuals (Pipeline, PipeRun, Level, Material, Spec) |
| `bim-objects.ttl` | 13 MB | 12,009 typed instances with data properties |
| `bim-spatial.ttl` | 12 MB | 220,346 adjacentTo triples |

</details>

<details>
<summary><b>Graph Analytics (Phase 4)</b></summary>

### Construction Precedence DAG

3가지 제약에서 시공 선후 관계를 추출:
1. **Class order**: Equipment → Structure → Piping → Electrical → HVAC
2. **Vertical order**: 낮은 고도 먼저
3. **Adjacency interference**: 인접 + 같은 클래스 → 아래쪽 먼저

### Adjacency 3단계 분류 (Finding M2)

| Tier | 조건 | 간선 수 | Critical chain |
|------|------|--------:|--------------:|
| Strong | touch (surface contact) | 13,422 | 17 steps |
| Strong+Medium | + small overlap | 86,644 | 53 steps |
| All (unfiltered) | 전체 | 220,346 | 88 steps |

### Neo4j Graph Database

```bash
docker start bimkg-neo4j  # http://localhost:7474 (neo4j/bimkg2026)
```

12,185 노드 + 285,035 간선 (ADJACENT_TO, MUST_PRECEDE, HAS_PARENT, BELONGS_TO_PIPELINE, IN_ZONE)

</details>

<details>
<summary><b>Findings</b></summary>

| ID | Severity | Title | Status |
|----|:--------:|-------|--------|
| M1 | MAJOR | XLSX substring matching misclassifies Piping | ✅ Fully Resolved |
| M2 | MINOR | Adjacency is AABB-based — 3-tier classification | ✅ Resolved |
| M3 | MAJOR | Parent box 448 objects contaminate 66% adjacency | ✅ Resolved locally |

상세: [`docs/findings/`](docs/findings/)

</details>

<details>
<summary><b>Development</b></summary>

```bash
make install    # uv pip install -e ".[dev]"
make test       # pytest (290 tests)
make lint       # ruff check
make format     # ruff format
```

**Conventions**: [dev-standards@0.1.0](https://github.com/tygwan/dev-standards) (R1-R9)
- R2: Task logging (5-section format)
- R3: Finding archival (6-step process)
- R4: Decision records (D1-D11)
- R5: Git workflow (atomic commits)
- R9: Provenance (SNAPSHOT pinned)

</details>
