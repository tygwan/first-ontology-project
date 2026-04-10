# BIM Ontology/KG Pipeline — Implementation Plan

## Context

**문제**: SP3D 기반 플랜트 BIM 모델(12,009 객체, 110K 공간 관계)에서 추출한 데이터가 있으나,
온톨로지 스키마(TBox)가 없고, 품질 검증 규칙이 없으며, LLM 기반 자연어 질의가 불가능한 상태.
현재 프로젝트에 코드가 전혀 없고(외부 C# 백엔드 + Python 스크립트가 처리), 데이터와 문서만 존재.

**목표**: 이 저장소 안에 Python 기반 완전한 파이프라인을 구축.
```
[BIM Data] → [Ingestion] → [Ontology/KG] → [Quality/Reasoning] → [Analytics] → [LLM Service] → [API/UI]
```

**데이터 원본**: `data/raw/dxtnavis/2026-04-07/` 단일 스냅샷 (DXTnavis v1.4.0, 2026-04-07 18:46:50 추출)
**기존 산출물**: SQLite DB(259MB, 11 tables), PowerBI star schema(12 CSV), Neo4j CSV(5 batches), 분석 문서 4건

---

## Phase 0: Project Bootstrap [S, 1일]

**목표**: Python 패키지 구조 + 의존성 + 테스트 인프라 구축

**생성 파일**:
- `pyproject.toml` — 의존성: rdflib, pyshacl, networkx, fastapi, uvicorn, streamlit, anthropic, pydantic, pytest, httpx, owlrl
- `src/bimkg/__init__.py`
- `src/bimkg/config.py` — 경로 상수 (PROJECT_ROOT, DATA_RAW, SQLITE_DB, POWERBI_DIR)
- `tests/conftest.py` — SQLite read-only 연결 fixture
- `.gitignore`

**검증**: `pip install -e ".[dev]"` 성공, `pytest` 실행 가능, `from bimkg.config import SQLITE_DB` 동작

---

## Phase 1: Ingestion + Data Quality [M, 4일]

**목표**: 9개 Insight 기반 데이터 품질 수정, 엔지니어링 속성 승격, PowerBI CSV 재생성

### 1a. 데이터 정제 (`src/bimkg/ingest/clean.py`)

| 수정 | 근거 | SQLite 변경 |
|------|------|-------------|
| "Other" 분할 → Container + Uncategorized | Insight 1: 3,353 singleton/no-mesh = Container | `refined_class` 컬럼 |
| Obstruction Volume 필터 | Insight 8: degree 5,267 이상치 | `is_analysis_volume` 플래그 |
| constructionType 좌표 오염 36건 | 데이터 품질 이슈 | NULL 처리 |
| SourceFileName 복구 | Insight 6: 0.008% → ~100% | `raw_properties_json`에서 추출 |
| EquipmentName 153건 복구 | Insight 6 | display_name 패턴 매칭 |
| Producer adjacency 직접 사용 | Insight 2: AABB precision 35.4% | `adjacency.csv` → 새 테이블 |

### 1b. 단위 파서 (`src/bimkg/ingest/unit_parser.py`)

`raw_properties_json` 안의 문자열 값을 SI 단위로 파싱:
- `"17 ft  1.48 in"` → 5.2248 m
- `"0 lbm"` → 0.0 kg
- `"150 # (RF)"` → (정격 등급, 별도 처리)

### 1c. SQLite 스키마 확장 (`src/bimkg/ingest/sqlite_enrich.py`)

기존 `dxtnavis-semantic.db`에 새 테이블 추가 (기존 테이블 유지):

```sql
-- 핵심 정제 테이블
bim_objects (object_id PK, parent_id, display_name, refined_class, level,
  system_path, pipeline, piperun, equipment_name, construction_type,
  location_text, status, is_analysis_volume, is_container, in_giant_group,
  centroid_x/y/z, bbox_volume_m3, bbox_diagonal_m, mesh_quality,
  vertex_count, triangle_count, has_real_mesh,
  dry_weight_kg, length_m, design_pressure_kpa, design_temperature_c,
  material, spec_name, npd)

-- 생산자 인접성 (AABB 대체)
bim_adjacency (source_object_id, target_object_id, relation_type,
  distance_m, overlap_volume_m3)

-- 계층 편의 테이블
bim_hierarchy (object_id PK, parent_id, level, path_root, path_system)

-- 연결 그룹
bim_connected_groups (group_id, object_id, element_count, is_giant)
```

### 1d. PowerBI CSV 재생성 (`src/bimkg/ingest/powerbi_export.py`)

- `dim_class.csv`: 5 → 7 클래스 (Container, Uncategorized 추가)
- `fact_objects.csv`: `refined_class` 사용 + SI 단위 물리량 컬럼 추가
- 신규: `dim_material.csv`, `dim_spec.csv` (공유 참조 노드)
- 기존 컬럼명 유지 (하위 호환)

**핵심 소스 파일**:
- `data/raw/dxtnavis/2026-04-07/AllProperties_20260407_184650.csv` (136 컬럼 원본)
- `data/raw/dxtnavis/2026-04-07/adjacency.csv` (110,173 producer edges)
- `data/working/dxtnavis/dxtnavis-semantic.db` (기존 SQLite, `raw_properties_json` 포함)

**테스트** (`tests/test_ingest/`):
- Container ~3,353건, Uncategorized ~2,564건 분류 검증
- 단위 파싱 엣지 케이스 (한국어 혼합, 빈 값, 단위 없는 숫자)
- PowerBI FK 무결성 + 중복 0 검증

**검증**: `bim_objects` 12,009행, `bim_adjacency` 110,173행, PowerBI CSV sanity check 통과

---

## Phase 2: OWL Ontology + RDF 인스턴스 [L, 6일]

**목표**: BIM 온톨로지 TBox(클래스 계층, 속성, 제약) 정의 + ABox(개체) 생성

### 2a. 네임스페이스 (`src/bimkg/ontology/namespaces.py`)

기존 `spatial_relationships.ttl`의 URI 체계 계승:
```
bim:   = http://example.org/bim-ontology/
inst:  = http://example.org/bim-ontology/instance/
spatial: = http://example.org/bim-ontology/spatial/
```

### 2b. OWL 스키마 (`src/bimkg/ontology/schema.py`)

클래스 계층:
```
bim:BIMObject
  bim:PhysicalObject
    bim:PipingComponent
    bim:StructuralMember
    bim:Equipment
      (Eqp Type 0/1/2/3 하위 계층 — raw_properties_json에서 추출)
    bim:Support
    bim:UncategorizedObject
  bim:Container
  bim:AnalysisVolume

bim:Context
  bim:Pipeline, bim:PipeRun, bim:SystemPathNode, bim:LevelNode, bim:ConnectedGroup

bim:Material
bim:Specification
bim:ConstructionTask
```

Object Properties (도메인 → 레인지):
- `bim:adjacentTo` (symmetric), `bim:overlaps` (symmetric), `bim:touches` (symmetric)
- `bim:belongsToPipeline` PipingComponent → Pipeline
- `bim:hasParent` BIMObject → BIMObject
- `bim:hasMaterial` PhysicalObject → Material
- `bim:hasSpecification` PhysicalObject → Specification

Data Properties: objectId, displayName, centroid, dryWeight, designPressure 등 (SI 단위, xsd 타입)

**출력**: `data/ontology/bim-ontology.owl` (TBox)

### 2c. 인스턴스 생성 (`src/bimkg/ontology/instances.py`)

SQLite `bim_objects` + `bim_adjacency` → RDF 트리플:
- ~12,009 개체 (typed by refined_class)
- ~110,173 공간 관계 트리플
- ~157 Pipeline + ~334 PipeRun + ~10 Level 공유 참조 개체
- Material/Specification 공유 개체 (동일 값 → 동일 URI)

**출력**: `data/ontology/bim-instances.ttl` (ABox, ~60-80 MB 예상)

**테스트**: OWL 로드 성공, SPARQL `COUNT bim:Equipment` = 660, Pipeline 멤버십 = 2,926

---

## Phase 3: SHACL 검증 + OWL 추론 [M, 4일]

**목표**: 데이터 품질 규칙을 SHACL 형상으로 기계 검증 + 암묵적 트리플 추론

### 3a. SHACL 형상 (`src/bimkg/validation/shapes.py`)

| Shape | 대상 | 제약 |
|-------|------|------|
| PipingMustHavePipeline | PipingComponent | belongsToPipeline minCount 1 |
| EquipmentMustHaveName | Equipment | displayName 패턴 매칭 |
| PhysicalObjectMustHaveMesh | PhysicalObject | vertexCount > 0 |
| PipingLevelGuard | PipingComponent | onLevel in {6,7,8} |
| NoAnalysisVolumeInGraph | AnalysisVolume | adjacentTo maxCount 0 |
| WeightNonNegative | PhysicalObject | dryWeight >= 0 |

**출력**: `data/ontology/bim-shapes.ttl`

### 3b. 검증 러너 (`src/bimkg/validation/validate.py`)

pySHACL 실행 → 구조화 리포트 → SQLite `bim_validation_results` 테이블 → PowerBI `fact_validation_shacl.csv`

### 3c. OWL 추론 (`src/bimkg/validation/reasoner.py`)

owlrl로 추론:
- Symmetric closure: adjacentTo 단방향 → 양방향
- Subclass: PipingComponent → PhysicalObject → BIMObject
- Domain/Range: belongsToPipeline 호출 시 → PipingComponent 추론

**출력**: `data/ontology/bim-inferred.ttl`

**테스트**: 알려진 위반 탐지 (Equipment 153건 이름 누락), symmetric closure 검증

---

## Phase 4: Graph Analytics [M, 5일]

**의존**: Phase 1 (Phase 2-3과 병렬 가능)

**목표**: NetworkX 기반 그래프 분석, 공간 존 분석, 스케줄 최적화

### 4a. 그래프 메트릭 (`src/bimkg/analytics/metrics.py`)

`bim_adjacency`에서 NetworkX 그래프 구축 (Container + AnalysisVolume 제외):
- Degree centrality → 구조적 허브 식별
- Betweenness centrality → 서브시스템 간 교량 객체
- Louvain community detection → 자연스러운 시공 존
- Clustering coefficient → 장비 이웃 밀집도

```sql
CREATE TABLE bim_graph_metrics (
  object_id TEXT PK, degree INT, degree_centrality REAL,
  betweenness_centrality REAL, clustering_coefficient REAL, community_id INT)
```

### 4b. 공간 분석 (`src/bimkg/analytics/spatial.py`)

- 15m 격자 존 분석: 객체 밀도, 클래스 혼합, 총 중량
- Pipeline 공간 범위: 각 Pipeline의 BBox extent + 교차 Pipeline
- 레벨별 통계

### 4c. 스케줄 분석 (`src/bimkg/analytics/schedule.py`)

- 기존 synth schedule 재검증
- Louvain community 기반 대안 스케줄 (50-200 그룹)
- 그래프 위상 + 중량 기반 크리티컬 패스

**PowerBI 출력**: `dim_community.csv`, `fact_graph_metrics.csv`, `fact_zone_density.csv`

**테스트**: Giant component = 8,626, 필터 후 노드 수 = ~8,656, Louvain 그룹 50-200개

---

## Phase 5: LLM / GraphRAG [L, 7일]

**의존**: Phase 1-4 완료

**목표**: Claude API 기반 자연어 BIM 질의

### 5a. 컨텍스트 검색 (`src/bimkg/llm/retriever.py`)

다중 전략:
1. SQLite FTS5 텍스트 검색 (display_name, pipeline, system_path)
2. 그래프 탐색: 발견된 객체의 N-hop 이웃, community, pipeline 형제
3. 분석 컨텍스트: 사전 계산된 메트릭 포함
4. SPARQL: 구조화 질의는 RDF 그래프에 직접

### 5b. 프롬프트 + 클라이언트 (`src/bimkg/llm/prompts.py`, `client.py`)

예시 질의:
- "P-10147 파이프라인의 자재 구성은?"
- "Level 7에서 가장 혼잡한 구역은?"
- "Equipment E-101 주변 구조물 목록"

Claude API (claude-sonnet-4-6) 래핑, 스트리밍 응답, 소스 인용

**테스트**: "P-10147 객체 수" → 129 포함 답변, Mock API 기반

---

## Phase 6: FastAPI Backend [M, 5일]

**의존**: Phase 1-5

**목표**: REST API로 전체 파이프라인 노출

**엔드포인트**:
| Router | 주요 API |
|--------|---------|
| `/objects` | GET 목록(필터: class/level/pipeline), GET /{id} 상세, GET /{id}/neighbors |
| `/graph` | GET /metrics/{id}, GET /communities, GET /path/{src}/{tgt} |
| `/ontology` | GET /classes (계층), GET /sparql (SPARQL 엔드포인트), GET /validate |
| `/analytics` | GET /summary, GET /zones, GET /pipelines, GET /schedule |
| `/llm` | POST /query (자연어), POST /explain/{id} (객체 설명) |

**파일**: `src/bimkg/api/main.py`, `src/bimkg/api/routers/*.py`

**검증**: `uvicorn bimkg.api.main:app` 기동, `/docs` OpenAPI 확인, 전 엔드포인트 JSON 응답

---

## Phase 7: Streamlit UI [M, 6일]

**의존**: Phase 6

**목표**: 인터랙티브 프로토타입 대시보드

**페이지**:
| 페이지 | 내용 |
|--------|------|
| Overview | KPI 카드 + 클래스 분포 + 메시 품질 |
| Object Explorer | 검색 + 상세 + 인접 객체 + 2D 산점도 |
| Graph View | 허브 시각화 + 커뮤니티 + 경로 탐색 |
| Ontology Browser | 클래스 트리 + SHACL 리포트 + SPARQL 박스 |
| Analytics | 존 히트맵 + Pipeline 비교 + 스케줄 간트 |
| LLM Chat | 자연어 질의 + 스트리밍 응답 + 소스 인용 |

**파일**: `src/bimkg/ui/app.py`, `src/bimkg/ui/pages/`

**검증**: `streamlit run src/bimkg/ui/app.py` 기동, 6 페이지 렌더링, 8,656 객체 산점도 3초 이내

---

## 의존성 그래프

```
Phase 0 (Bootstrap)
   │
   v
Phase 1 (Ingest/Clean) ──────────┐
   │                              │
   v                              v
Phase 2 (Ontology)          Phase 4 (Analytics)
   │                              │
   v                              │
Phase 3 (SHACL/Reasoning)        │
   │                              │
   └──────────┬───────────────────┘
              v
        Phase 5 (LLM/GraphRAG)
              │
              v
        Phase 6 (FastAPI)
              │
              v
        Phase 7 (Streamlit UI)
```

Phase 2-3과 Phase 4는 **병렬 진행 가능** (둘 다 Phase 1에만 의존).

---

## Target 프로젝트 구조

```
first-ontology-project/
  pyproject.toml
  src/bimkg/
    __init__.py
    config.py
    ingest/     (clean.py, unit_parser.py, sqlite_enrich.py, powerbi_export.py)
    ontology/   (namespaces.py, schema.py, instances.py)
    validation/ (shapes.py, validate.py, reasoner.py)
    analytics/  (metrics.py, spatial.py, schedule.py)
    llm/        (retriever.py, prompts.py, client.py)
    api/        (main.py, routers/)
    ui/         (app.py, pages/)
  tests/
    conftest.py
    test_ingest/ test_ontology/ test_validation/ test_analytics/ test_llm/ test_api/
  data/
    raw/dxtnavis/2026-04-07/   (읽기 전용, 변경 없음)
    working/dxtnavis/           (SQLite에 새 테이블 추가)
    powerbi/2026-04-07/         (CSV 재생성)
    ontology/                   (신규: OWL, TTL, SHACL 파일)
  docs/
    plan/                       (이 계획서)
```

---

## 핵심 참조 파일

| 파일 | 용도 |
|------|------|
| `data/raw/dxtnavis/2026-04-07/AllProperties_20260407_184650.csv` | 12,009 × 136 원본 속성 |
| `data/raw/dxtnavis/2026-04-07/adjacency.csv` | 110,173 producer 공간 관계 |
| `data/raw/dxtnavis/2026-04-07/geometry.csv` | BBox, centroid, mesh 메타 |
| `data/raw/dxtnavis/2026-04-07/validation.csv` | 메시 품질, verdict |
| `data/raw/dxtnavis/2026-04-07/connected_groups.csv` | 3,355 연결 그룹 |
| `data/working/dxtnavis/dxtnavis-semantic.db` | 259MB SQLite (raw_properties_json 포함) |
| `docs/dxtnavis-2026-04-07-baseline-insights.md` | 9개 인사이트 (Phase 1 수정 근거) |
| `docs/dxtnavis-2026-04-07-powerbi-integration.md` | Star schema 명세 |

---

## 리스크

| 리스크 | 대응 |
|--------|------|
| rdflib 80MB TTL 성능 | N-Triples 직렬화 또는 Oxigraph 전환 |
| 단위 파서 엣지 케이스 | 포괄 테스트 + null fallback |
| AABB 폐기 시 기존 분석 차이 | producer adjacency로 전환, 기존 테이블 보존 |
| PowerBI dim 변경 → 기존 대시보드 호환 | 컬럼 추가 전략, 이름 변경 없음 |

---

## 총 일정

| Phase | 일수 | 누적 |
|-------|------|------|
| 0: Bootstrap | 1 | 1 |
| 1: Ingest/Clean | 4 | 5 |
| 2: Ontology | 6 | 11 |
| 3: SHACL/Reasoning | 4 | 15 |
| 4: Analytics (2-3 병렬) | 5 | 15 |
| 5: LLM/GraphRAG | 7 | 22 |
| 6: FastAPI | 5 | 27 |
| 7: Streamlit UI | 6 | 33 |

**총 ~5주**, 각 Phase 완료 시마다 독립적으로 검증 가능한 산출물 생성.

---

## 실행 시 첫 단계

1. 이 계획서를 `docs/plan/pipeline-implementation-plan.md`로 복사
2. Phase 0 시작: `pyproject.toml` + `src/bimkg/` 패키지 구조 생성
