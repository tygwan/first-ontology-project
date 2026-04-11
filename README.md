# Ontology for Construction Management

> SP3D 기반 플랜트 BIM 모델(12,009 객체 × 110,173 공간 관계)을
> **온톨로지 기반 지식 그래프**로 변환하여 자연어 질의·품질 검증·
> 시공 분석·시각화가 가능한 파이프라인을 Python 단일 저장소로 제공합니다.

**Pipeline**: `BIM → Ingest → Ontology → Quality → Analytics → LLM → API/UI`

**Data**: [DXTnavis](https://github.com/tygwan/DXTnavis) v1.4.0 snapshot `2026-04-07`
**Target platform**: Palantir Foundry (Developer Tier)

## Quick Start

```bash
# Python 3.12 + uv
uv venv --python 3.12
uv pip install -e ".[dev]"

# Run tests
pytest
```

## Documentation

- **🗂 [Project Journal](docs/PROJECT-JOURNAL.md)** — **단일 포털**: 프로젝트에서 마주한 문제, 결정, 타임라인을 한 문서에서 내비게이션
- **[Implementation Plan](docs/plan/pipeline-implementation-plan.md)** — 7단계 파이프라인 전체 계획
- **[Phase 1a Design](docs/analysis/phase-1a-data-realignment-design.md)** — 데이터 정렬 설계 결정
- **[RefinedXlsxExporter Logic](docs/analysis/refined-xlsx-exporter-logic.md)** — XLSX 분류 로직 분석
- **[Findings Archive](docs/findings/)** — 발견된 데이터 이슈 + 증거 자료
- **[Task Logs](docs/tasklog/)** — 단계별 작업 기록
- **[Reference Docs](docs/reference/)** — DXTnavis 데이터 명세 및 baseline 분석

<details>
<summary><b>📁 Project Structure</b></summary>

```
first-ontology-project/
├── README.md                     # 이 문서
├── pyproject.toml                # 패키지 정의, 의존성, CLI entry points
├── Makefile                      # install / test / lint / format 타겟
│
├── data/                         # 전체 gitignored
│   ├── raw/                      # Bronze — DXTnavis 원본 (읽기 전용)
│   │   └── dxtnavis/2026-04-07/
│   ├── clean/                    # Silver — 타입 정규화 + 스키마 통일
│   │   └── 2026-04-07/
│   ├── enriched/                 # Gold — 조인 + 플래그 + SI 단위 + lineage
│   │   └── 2026-04-07/
│   ├── ontology/                 # Foundry-ready Object Types + Link Types
│   │   └── 2026-04-07/
│   │       ├── object_types/
│   │       ├── link_types/
│   │       └── owl/
│   ├── powerbi/                  # Phase 1d PowerBI star schema
│   │   └── 2026-04-07/
│   └── backup/                   # 동결된 legacy (C# 백엔드 산출물)
│       └── dxtnavis-csharp-20260411/
│
├── docs/
│   ├── reference/                # 외부 참조 문서
│   ├── analysis/                 # 설계 결정 문서
│   ├── plan/                     # 구현 계획
│   └── tasklog/                  # 작업 완료 기록
│
├── src/bimkg/
│   ├── config.py                 # 모든 경로 상수 + 예상 카운트
│   └── ingest/                   # Phase 1 — 정제, 파서, 분류기
│       ├── unit_parser.py        # SP3D 문자열 → SI 단위
│       └── xlsx_classifier.py    # RefinedXlsxExporter 로직 Python 포트
│
└── tests/
    ├── conftest.py
    ├── test_config.py
    └── test_ingest/
```

</details>

<details>
<summary><b>🏗️ Pipeline Architecture (7 Phases)</b></summary>

| Phase | 이름 | 역할 | 기술 |
|:-----:|------|------|------|
| **0** | Bootstrap | Python 패키지, 의존성, 테스트 인프라 | uv, pytest, ruff |
| **1a** | Ingest (정제) | XLSX 로드 + 원본 CSV 조인 + 플래그 파생 | pandas, openpyxl |
| **1b** | Unit Parser | SP3D 문자열 ("17 ft 1.48 in") → SI (meters) | regex, pure functions |
| **1c** | SQLite Writer | `bimkg.db` 테이블 생성 및 데이터 쓰기 | sqlite3 |
| **1d** | Exports | PowerBI CSV + Parquet (Foundry-ready) | pyarrow |
| **2** | Ontology | OWL TBox + RDF ABox 생성 | rdflib |
| **3** | Quality | SHACL 검증 + OWL 추론 | pyshacl, owlrl |
| **4** | Analytics | 그래프 메트릭, 공간 분석, 시공 순서 | NetworkX |
| **5** | LLM | GraphRAG 자연어 질의 | Claude API |
| **6** | API | REST + SPARQL endpoint | FastAPI |
| **7** | UI | 대화형 대시보드 프로토타입 | Streamlit |

</details>

<details>
<summary><b>📊 Data Flow (Medallion Architecture)</b></summary>

Palantir Foundry 의 표준 패턴인 **Bronze / Silver / Gold / Ontology** 4계층 구조를 채택합니다.

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Bronze  │ →   │  Silver  │ →   │   Gold   │ →   │ Ontology │
│  (raw)   │     │ (clean)  │     │(enriched)│     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     ↓                ↓                ↓                  ↓
data/raw/        data/clean/     data/enriched/    data/ontology/
DXTnavis 원본    파싱+타입정규화   +플래그+SI+lineage  +Object/Link Types
CSV/XLSX/JSON    Parquet         Parquet + SQLite  Parquet + OWL/TTL
```

**각 계층의 책임**:

| 계층 | 변환 | 출력 포맷 | Foundry 매핑 |
|------|------|---------|-------------|
| Bronze | 없음 (원본 그대로) | CSV, XLSX, JSON | Landing zone dataset |
| Silver | 타입 캐스팅, 중복 제거, 스키마 검증, null 정책 | Parquet | Cleaned dataset |
| Gold | 다른 소스와 조인, 플래그 파생, 단위 변환, lineage 컬럼 | Parquet + SQLite | Business-ready dataset |
| Ontology | Object Type 별 분할, Link Type 링크 테이블 | Parquet, OWL, TTL | Ontology Object/Link Types |

</details>

<details>
<summary><b>🔧 Development Commands</b></summary>

```bash
# 환경 구성
make install              # uv pip install -e ".[dev]"

# 테스트
make test                 # pytest 전체 실행
pytest tests/test_ingest/ # 특정 모듈만

# 코드 품질
make lint                 # ruff check
make format               # ruff format

# 정리
make clean                # 빌드 아티팩트, 캐시 제거
```

CLI entry point (Phase 1c 이후 추가 예정):

```bash
# Phase 1a 전체 파이프라인 실행
bimkg ingest --snapshot 2026-04-07

# 개별 단계
bimkg classify --xlsx data/raw/...
bimkg export-powerbi --out data/powerbi/2026-04-07/
bimkg export-parquet --out data/ontology/2026-04-07/
```

</details>

<details>
<summary><b>🎯 Current Status</b></summary>

| Phase | 상태 | 테스트 | 커밋 |
|-------|------|-------|------|
| 0. Bootstrap | ✅ 완료 | 3/3 | `ddac7b4` |
| 1a. Ingest | 🔄 진행 중 | oracle 29/29 | `cf70da1` |
| 1b. Unit Parser | ✅ 완료 | 44/44 | `8bd8b43` |
| 1c. SQLite Writer | ⏸ 대기 | — | — |
| 1d. Exports | ⏸ 대기 | — | — |
| 2. Ontology | ⏸ 대기 | — | — |
| 3. Quality | ⏸ 대기 | — | — |
| 4. Analytics | ⏸ 대기 | — | — |
| 5. LLM | ⏸ 대기 | — | — |
| 6. API | ⏸ 대기 | — | — |
| 7. UI | ⏸ 대기 | — | — |

**Total tests**: 76/76 passing

</details>

<details>
<summary><b>🔗 Palantir Foundry Integration</b></summary>

이 프로젝트의 출력물은 **Palantir Foundry Developer Tier** 에 직접 import 가능하도록 설계되었습니다.

### Import 전략

1. **Raw datasets**: `data/raw/dxtnavis/2026-04-07/` 를 Foundry `/raw/dxtnavis/2026-04-07/` 로 업로드
2. **Cleaned datasets**: Phase 1a 의 Parquet 출력을 `/cleaned/bim-*` 으로 등록
3. **Enriched datasets**: Phase 1a 의 Gold 출력을 `/enriched/bim-*` 으로 등록
4. **Ontology datasets**:
   - `object_types/piping.parquet` → Object Type `PipingComponent`
   - `object_types/structural.parquet` → Object Type `StructuralMember`
   - `link_types/adjacent_to.parquet` → Link Type `AdjacentTo`
   - ...

### Object Type 매핑 (예정)

| Parquet file | Foundry Object Type | Primary Key | Title |
|-------------|--------------------|:-----------:|-------|
| piping.parquet | PipingComponent | object_id | display_name |
| structural.parquet | StructuralMember | object_id | display_name |
| equipment.parquet | Equipment | object_id | display_name |
| electrical.parquet | ElectricalComponent | object_id | display_name |
| hvac.parquet | HvacComponent | object_id | display_name |
| container.parquet | Container | object_id | display_name |

Object Type 전략 (Flat vs Per-class vs Property-Sets) 는 Phase 1a 완료 후 데이터를 확인하고 결정합니다.

### Developer Tier 고려사항

- Dataset 크기 제한: 본 프로젝트 규모 (12K objects + 110K edges) 는 여유
- Ontology 복잡도 최소화
- Actions / Functions 는 Phase 6-7 에서 고려

</details>

<details>
<summary><b>📝 Repository Conventions</b></summary>

- **Python version**: 3.12+ (type hints 사용, `from __future__ import annotations`)
- **패키지 매니저**: `uv` (pip/venv 대신)
- **코드 스타일**: `ruff` (line length 100)
- **테스트**: `pytest`, fixture 는 `tests/conftest.py`
- **Task logging**: 모든 작업 완료 시 `docs/tasklog/phase-*.md` 에 5-section 로그 작성
  - 언어/내용, 문제, 분석, 해결방안, 결과
- **Commit message**: `Phase X: brief description` + 설명 + `Co-Authored-By`
- **Data directory**: 전체 gitignored. 원본은 프로젝트 관리자가 별도 보관

</details>
