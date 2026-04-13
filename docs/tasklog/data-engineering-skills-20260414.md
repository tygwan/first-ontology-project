# Data Engineering 스킬 적용 — Airflow + OpenLineage + Profiling + Catalog + Lineage

**일자**: 2026-04-14
**담당 Task**: #36, #37, #38, #39, #40
**커밋**: (pending)

---

## 1. 언어 / 내용

`data` / `data-engineering` 플러그인의 스킬을 BIM 파이프라인에 적용해
**Data Engineer / Data Analyst / Data Scientist / Database Optimizer** 4관점의
포트폴리오 자료를 생성. 5개 항목 모두 완료.

| # | 산출물 | 입력 | 출력 |
|:-:|--------|------|------|
| 1 | Airflow DAG (`dags/bim_pipeline_dag.py`) | 7 Phase 함수 | 7 PythonOperator + 14 Asset |
| 2 | OpenLineage emitter (`src/bimkg/lineage/`) | Phase 메타데이터 | 14 events JSONL (295 KB) |
| 3 | ydata-profiling 리포트 (`scripts/profile_gold_table.py`) | Gold parquet 2개 | 28 MB HTML 리포트 + summary.json |
| 4 | Warehouse 카탈로그 (`scripts/warehouse_catalog.py`) | SQLite 7 table | catalog.md (5 KB) + catalog.json (86 KB) |
| 5 | Lineage 추적 (`scripts/trace_lineage.py`) | OpenLineage events | impact-analysis.md + lineage-graph.png |

### 1.1 신규/수정 파일

```
dags/
└── bim_pipeline_dag.py                              # NEW (Airflow 3.x DAG)

src/bimkg/lineage/                                   # NEW package
├── __init__.py
└── openlineage_emitter.py                           # 14 events with Schema/ColumnLineage facets

scripts/
├── emit_lineage.py                                  # NEW
├── profile_gold_table.py                            # NEW
├── warehouse_catalog.py                             # NEW
└── trace_lineage.py                                 # NEW

data/lineage/2026-04-12/
├── openlineage-events.jsonl                         # 14 events, 295 KB
└── openlineage-summary.json

docs/reference/profiling/2026-04-12/
├── bim_objects_enriched.html                        # 25.4 MB
├── bim_adjacency_sym.html                           # 2.9 MB
└── summary.json                                     # 270 quality alerts

docs/reference/warehouse-catalog/2026-04-12/
├── catalog.md
└── catalog.json

docs/reference/lineage/2026-04-12/
├── impact-analysis.md                               # downstream/upstream maps
├── lineage-graph.json
├── lineage-graph.dot
└── lineage-graph.png                                # 822 KB rendered graph

pyproject.toml                                       # +apache-airflow, +openlineage-python
```

---

## 2. 문제

**컨텍스트**: Foundry 데이터셋 6개 + Object Type 6개 등록까지 완료한 상태에서,
다음 단계로 **데이터 엔지니어링 도구 체계** 를 도입할 시점. JD 와 포트폴리오 관점에서
파이프라인 자동화 / 메타데이터 관리 / 데이터 품질을 단일 사례로 묶어 보여줄 자료가 부족.

**4관점 별 갭**:
- **Data Engineer**: 수동으로 호출되는 7개 Phase 함수가 자동화/스케줄링/재현성 없음
- **Data Analyst**: Gold 219 컬럼의 quality / 분포 / 결측 파악이 안 됨 (대시보드 만들기 전 단계 누락)
- **Database Optimizer (DBA)**: SQLite 스키마/인덱스/storage 메타가 문서화 안 됨
- **Data Scientist**: dataset 변경 시 downstream 영향 범위를 알 수 없음 (모델 재학습 트리거 판단 불가)

---

## 3. 분석

### 3.1 도구 선택

| 항목 | 선택 | 이유 |
|------|------|------|
| Orchestrator | **Apache Airflow 3.x** | 가장 표준적인 ETL 오케스트레이터. Asset (구 Dataset) 으로 lineage 내장 |
| Lineage 표준 | **OpenLineage v2** | Marquez/DataHub/Atlan/Foundry 가 모두 지원하는 표준. airflow-openlineage 와 동일한 facets |
| Profiling | **ydata-profiling 4.18** | 변수 타입 자동 추론 + 270개 alert 자동 도출 (constant, imbalanced, skewed, missing) |
| Catalog | 직접 작성 | DBA 관점의 storage / index / FK 메타데이터를 SQLite PRAGMA 로 추출 |
| Lineage 추적 | **OpenLineage events 파싱** | 동일 events 를 두 번 활용 (emit → trace), 단일 진실 원천 (single source of truth) |

### 3.2 Airflow 3.x 호환성

- 초기 DAG 작성 시 `from airflow import DAG`, `from airflow.datasets import Dataset` 사용 → 3.x 에서 import 실패
- 3.x 에서 `Dataset` → **`Asset`** 으로 rename, `airflow.sdk` 로 이동
- `airflow.operators.python.PythonOperator` → **`airflow.providers.standard.operators.python.PythonOperator`**
- 해결: `from airflow.sdk import DAG, Asset as Dataset` 로 alias

### 3.3 OpenLineage facets 설계

각 Phase 별로 다음 facets 를 부여:

| Facet | 값 |
|-------|---|
| `JobTypeJobFacet` | processingType=BATCH, integration=PYTHON, jobType=PIPELINE |
| `SourceCodeLocationJobFacet` | git URL + revision (실시간 `git rev-parse HEAD`) |
| `OwnershipJobFacet` | bimkg-team (MAINTAINER) |
| `SchemaDatasetFacet` | parquet/csv 스키마 자동 추출 (pandas dtypes) |
| `DatasourceDatasetFacet` | `file://`, `sqlite://`, `palantir-foundry://` 3 namespace |
| `ColumnLineageDatasetFacet` | Bronze 컬럼 → Gold 컬럼 매핑 (예: `is_container ← validation.verdict + connected_groups.group_size`) |
| `OutputStatisticsOutputDatasetFacet` | rowCount + size |
| `NominalTimeRunFacet` | snapshot 일자 |
| `ProcessingEngineRunFacet` | pandas 2.3.3 |

### 3.4 ydata-profiling 튜닝

- `correlations`: Pearson 만 계산 (Spearman/Kendall/PhiK/Cramer V 비활성 → 219 컬럼에서 너무 무거움)
- `interactions.continuous=False`: pairwise scatter 220개 컬럼 = 폭발 방지
- `missing_diagrams.heatmap=False`: 대신 matrix + bar 만
- 한국어 column name 으로 인한 matplotlib glyph warning 발생 (DejaVu Sans 폰트에 한글 없음) — 데이터 무결성에는 무영향

### 3.5 Lineage tracing 알고리즘

OpenLineage events JSONL → 양방향 인접 리스트:
- `producers[ds] = [job, ...]` (이 dataset 을 만드는 job)
- `consumers[ds] = [job, ...]` (이 dataset 을 소비하는 job)
- `job_inputs[job] = [ds, ...]`, `job_outputs[job] = [ds, ...]`
- 재귀 DFS 로 downstream / upstream 그래프 생성

---

## 4. 해결

### 4.1 Airflow DAG (#1)

7 PythonOperator + 14 Asset (Bronze 6 + Gold 3 + Output 5):
```python
phase_1a >> [phase_1d_powerbi, phase_1d_foundry, phase_2_tbox, phase_4_neo4j]
[phase_1a, phase_2_tbox] >> phase_2_abox
phase_2_tbox >> phase_3_shacl
```

### 4.2 OpenLineage emitter (#2)

`scripts/emit_lineage.py` → 14 events (각 Phase 별 START + COMPLETE):
- Phase 1a: 6 입력 / 3 출력 (column lineage 6 매핑 포함)
- Phase 1d Foundry: 2 입력 / 10 출력 (palantir RID 포함)
- 기타 Phase: 0~3 입력 / 1 출력

### 4.3 Profiling 리포트 (#3)

`bim_objects_enriched`: 12,009 × 219, **48.4% missing cells**, **270 alerts**:
- 31 constant columns (제거 후보)
- 70+ columns with >80% missing (sparse SP3D 필드)
- `object_id` unique (PK 검증)
- `bbox_volume_m3`, `dry_weight_kg` highly skewed (long-tail)

`bim_adjacency_sym`: 220,346 × 10, **0% missing**, 6 alerts (distance_m 85% zeros = touching)

### 4.4 Warehouse 카탈로그 (#4)

`scripts/warehouse_catalog.py` → catalog.md / catalog.json:
- Storage: **62.9 MB**, 16,106 pages × 4 KB, journal_mode=delete, freelist 137
- 7 tables (3 physical + 4 FTS shadow), 219 columns documented
- Recommended indexes: `refined_class`, `pipeline`, `level`, `is_container`, `is_analysis_volume`, `source_object_id`, `target_object_id`
- Logical FK: `bim_adjacency.{source,target}_object_id → bim_objects.object_id`

### 4.5 Lineage 추적 (#5)

`scripts/trace_lineage.py` → 양방향 영향 분석:
- 24 datasets, 7 jobs
- 예: `AllProperties_20260407_184650.csv` 변경 시 → enriched parquet, PowerBI, 10 Foundry datasets, OWL ABox, Neo4j 모두 재생성 필요 (downstream 13개)
- DOT + PNG 시각화 (graphviz 없으면 networkx + matplotlib fallback)

---

## 5. 결과

### 5.1 산출물 요약

| Skill | Output | Size | Time |
|-------|--------|-----:|-----:|
| Airflow DAG | `dags/bim_pipeline_dag.py` | 6 KB | DAG load < 1s |
| OpenLineage events | 14 events JSONL | 295 KB | emit < 5s |
| Profile (objects) | HTML report | 25.4 MB | 98s |
| Profile (adjacency) | HTML report | 2.9 MB | 7s |
| Warehouse catalog | catalog.json + .md | 92 KB | < 5s |
| Lineage trace | impact-analysis.md + PNG | 870 KB | < 3s |

### 5.2 4관점 충족 확인

| 관점 | 산출물 | 확인 |
|------|--------|------|
| Data Engineer | Airflow DAG + OpenLineage events | 7 task DAG load 성공, lineage events 표준 준수 |
| Data Analyst | profiling HTML | 270 alerts, 변수 분포/missing/correlations 확인 가능 |
| Data Scientist | column lineage + impact analysis | Bronze 변경 시 downstream 13 artifacts 식별 가능 |
| DBA | warehouse catalog + recommended indexes | 62.9 MB SQLite 의 storage / index 권고안 문서화 |

### 5.3 dependency 추가

`pyproject.toml`:
```toml
"apache-airflow>=3.0",       # already installed (3.2.0)
"openlineage-python>=1.20",  # already installed
```

`ydata-profiling`, `setuptools<81` 은 별도 인스톨 (optional dev tool, pyproject 에 추가하지 않음).

### 5.4 Out of scope (이번 세션 아님)

- Phase 7 (Streamlit UI) — 별도 진행 예정
- Foundry Link Type 생성 — Save 오류 미해결
- Diagram (Figma) 수동 갱신 — 검토 문서 (`docs/analysis/medallion-data-flow-review.md`) 작성 완료, Figma 직접 수정은 MCP 미지원
