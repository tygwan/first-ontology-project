# Visualization Assets — Index

> 프로젝트 전체에서 생성한 시각화 / 다이어그램 / 분석 자료의 통합 인덱스.
> 카테고리: Architecture · Data Flow · Notebooks · Findings · BI Mockup · Engineering Reports.
>
> 각 자료는 생성 도구, 위치, 파일 수, 용도, 갱신 방법을 명시.

---

## 0. 한눈에 보기

| 카테고리 | 위치 | 파일 수 | 총 크기 | 도구 |
|----------|------|--------:|--------:|------|
| Architecture HTML | `portfolio/` | 1 (8 sections) | 68 KB | 손수 작성 (Figma 디자인 시스템) |
| Medallion Data Flow | Figma board (외부) | — | — | Figma FigJam (MCP plugin) |
| Notebook 분석 | `notebooks/figures/` | 25 PNG | 11 MB | matplotlib (5 notebooks) |
| Finding 시각화 | `docs/findings/*/figures/` | 4 PNG (M1) | 364 KB | matplotlib (audit 스크립트) |
| Power BI 페이지 mockup | `docs/analysis/powerbi-dashboard-preview/figures/` | 7 PNG | 1.1 MB | matplotlib (mockup 스크립트) |
| Profiling HTML 리포트 | `docs/reference/profiling/2026-04-12/` | 2 HTML + 1 JSON | 27 MB | ydata-profiling 4.18 |
| Lineage 그래프 | `docs/reference/lineage/2026-04-12/` | PNG + DOT + JSON + MD | 896 KB | OpenLineage + networkx |
| Warehouse 카탈로그 | `docs/reference/warehouse-catalog/2026-04-12/` | MD + JSON | 104 KB | sqlite PRAGMA + 자작 |
| Temp 캡처 (작업용) | `temp/` | 4 PNG | 408 KB | 화면 캡처 |

**합계**: 약 **41 MB**, 2 외부 자산 (Figma board 1 + 외부 PowerBI mockup 화면)

---

## 1. Architecture / 시스템 구조

### 1.1 `portfolio/architecture-diagrams.html` — Toss-style 종합 아키텍처 페이지

> 단일 HTML 에 8개 section 으로 시스템 전반을 시각화. Inter 폰트 + Figma 디자인 시스템 컬러 사용.

| Section | 내용 |
|---------|------|
| 1. Full Pipeline Architecture | Bronze → Silver → Gold → Analytics → Output 전체 흐름 |
| 2. Medallion Architecture | Layer 별 데이터셋 / 도구 매핑 |
| 3. OWL Ontology Class Hierarchy | BIMObject 계층, Properties (object/data) 시각화 |
| 4. Graph Analytics & KPI System | NetworkX 분석, Louvain, Precedence DAG, 33 KPIs |
| 5. LLM Agent Architecture | Gemini 2.5 Flash + 5 tools (SQL/FTS5/SPARQL/Cypher/KPI) |
| 6. REST API Endpoints | FastAPI 12 endpoints 구조 |
| 7. Data Quality Findings | M1/M2/M3 finding 요약 |
| 8. Technology Stack | 사용 라이브러리 + 버전 |

**열기**: 브라우저로 열거나 `python -m http.server 8000` 후 <http://localhost:8000/portfolio/architecture-diagrams.html>

### 1.2 Figma — Medallion Data Flow board (외부)

- **URL**: <https://www.figma.com/board/NE51FDJ9hFzOPJP5qgBxTU/Medallion-Data-Flow>
- **마지막 수정**: 2026-04-14 (Figma MCP plugin 으로 5개 fix 적용)
- **구조**: Bronze (6) → Silver (4) → Gold (4) → Analytics (4) → Output (6)
- **검토 문서**: [`docs/analysis/medallion-data-flow-review.md`](analysis/medallion-data-flow-review.md)
- **로컬 백업 PNG**: [`temp/Medallion Data Flow.png`](../temp/Medallion%20Data%20Flow.png) (수정 전 스냅샷)

### 1.3 OpenLineage Pipeline DAG (Lineage 그래프)

- **PNG**: [`docs/reference/lineage/2026-04-12/lineage-graph.png`](reference/lineage/2026-04-12/lineage-graph.png) (820 KB)
- **DOT**: [`docs/reference/lineage/2026-04-12/lineage-graph.dot`](reference/lineage/2026-04-12/lineage-graph.dot) (graphviz 로 다른 포맷 변환 가능)
- **포함**: 24 datasets + 7 jobs + 28 edges. Bronze (yellow) / Gold (green) / SQLite (blue) / Foundry (lavender) / Job (red) 색상 분류
- **갱신**: `.venv/bin/python scripts/emit_lineage.py && .venv/bin/python scripts/trace_lineage.py`

---

## 2. Notebook 분석 시각화

`notebooks/figures/` — 5개 노트북에서 생성된 25 PNG (DPI 300, matplotlib).

### Notebook 01 — EDA (`01_eda.ipynb`, 7 figures)

| 파일 | 내용 |
|------|------|
| `01_s1_column_fill_rate.png` | 219 컬럼별 결측률 막대 차트 |
| `01_s2_class_comparison.png` | refined_class 분포 (Piping/Equipment/...) |
| `01_s3_spatial_layout.png` | 12K 객체의 2D 산점도 (centroid_x/y, color=class) |
| `01_s4_pipeline_structure.png` | 157 Pipeline 별 객체 수 + spatial extent |
| `01_s5_graph_degree.png` | Adjacency degree distribution (long-tail) |
| `01_s6_equipment_gaps.png` | Equipment 식별 누락 153건 분석 |
| `01_s7_quality_suspects.png` | 분류 confidence LOW/LIKELY_BUG 요약 |

### Notebook 02 — Construction Management (`02_construction_management.ipynb`, 5 figures)

| 파일 | 내용 |
|------|------|
| `02_s1_weight_heatmap.png` | 50×50 격자 별 총 dry_weight_kg 히트맵 |
| `02_s2_zone_comparison.png` | 144 Louvain zones 의 size / weight 비교 |
| `02_s3_ab_metrics.png` | A/B (BBox vs Producer adjacency) 메트릭 비교 |
| `02_s4_pipeline_dispersion.png` | Pipeline 별 공간 분산 (bbox_diagonal_m) |
| `02_s5_zone_class_composition.png` | Zone 별 class mix (stacked bar) |

### Notebook 03 — Adjacency Tiers (`03_adjacency_tiers.ipynb`, 4 figures)

| 파일 | 내용 |
|------|------|
| `03_s1_relation_types.png` | Strong / Medium / Weak relation 분포 |
| `03_s2_tier_cross_class.png` | Tier × class crosstab (어떤 class 끼리 연결) |
| `03_s3_ab_precedence.png` | Strong+Medium DAG vs All DAG 의 Precedence 비교 |
| `03_s4_pipeline_case_study.png` | P-10147 case study (129 객체) |

### Notebook 04 — Construction Schedule (`04_construction_schedule.ipynb`, 4 figures)

| 파일 | 내용 |
|------|------|
| `04_s1_gantt_chart.png` | 44 step 시공 Gantt chart |
| `04_s2_spatial_wave.png` | 시공 wave 의 공간적 진행 (color=step) |
| `04_s3_dependency_matrix.png` | 18,214 edges 의존성 행렬 |
| `04_s4_critical_path.png` | Critical path 시각화 |

### Notebook 05 — KPI Dashboard (`05_kpi_dashboard.ipynb`, 5 figures)

| 파일 | 내용 |
|------|------|
| `05_s1_plant_overview.png` | Plant level KPI 카드 (4 levels) |
| `05_s2_equipment_criticality.png` | 660 Equipment 의 criticality 분포 |
| `05_s3_accessibility_isolation.png` | Accessibility × valve isolation 산점도 |
| `05_s4_zone_comparison.png` | 144 zones 의 KPI 비교 |
| `05_s5_pipeline_kpis.png` | 157 Pipeline 별 KPI 막대 |

**갱신**: 각 노트북 실행 → `notebooks/figures/` 자동 저장 (R3 visualization PNG rule 적용)

---

## 3. Finding 시각화

### 3.1 M1 — Piping Misclassification (`docs/findings/2026-04-12-M1-piping-misclassification/`)

| 파일 | 내용 |
|------|------|
| `figures/01_piping_confidence.png` | 분류 confidence 분포 |
| `figures/02_substring_bug_causes.png` | substring 매칭 버그의 원인 키워드 |
| `figures/03_likely_misclassified.png` | LIKELY_BUG 사례 |
| `figures/04_class_distribution.png` | XLSX vs Refined class 분포 |
| `data/*.csv` | 5 CSV (audit 결과) — 재현 가능한 증거 |
| `audit.py` | 재현 스크립트 |
| `make_figures.py` | 시각화 생성 스크립트 |

### 3.2 M2 — Adjacency Tiers / M3 — Parent Box Contamination

- 시각화 PNG 없음 (현재 README 텍스트 분석 위주)
- M2 결과의 시각적 표현은 `notebooks/figures/02_s3_ab_metrics.png` 와 `03_s2_tier_cross_class.png` 에 포함
- M3 결과는 `02_s5_zone_class_composition.png` 에 반영

---

## 4. Power BI Dashboard Mockup

`docs/analysis/powerbi-dashboard-preview/` — 7 페이지 mockup (Power BI 스크린샷 대체용).

| 파일 | 페이지 |
|------|--------|
| `figures/page1-overview.png` | Overview (KPI cards) |
| `figures/page2-classification-confidence.png` | Classification confidence |
| `figures/page3-spatial-distribution.png` | Spatial distribution |
| `figures/page4-pipelines.png` | Pipelines (157 pipelines) |
| `figures/page5-mesh-quality.png` | Mesh quality |
| `figures/page6-connected-groups.png` | Connected groups (3,355) |
| `figures/page7-physical-properties.png` | Physical properties (weight/length 분포) |
| `README.md` | mockup 사양 + 데이터 소스 매핑 (12 KB) |

**갱신**: `src/bimkg/ingest/exporters/powerbi.py` 출력을 입력으로 받는 mockup 스크립트로 재생성 가능.

---

## 5. Engineering / Data Quality Reports

### 5.1 Profiling HTML 리포트 (ydata-profiling)

`docs/reference/profiling/2026-04-12/`:

| 파일 | 크기 | 내용 |
|------|-----:|------|
| `bim_objects_enriched.html` | 25.4 MB | Gold 12,009 × 219 — 270 quality alerts (constant/imbalanced/missing/skewed/correlation) |
| `bim_adjacency_sym.html` | 2.9 MB | Adjacency 220,346 × 10 — 6 alerts |
| `summary.json` | 28 KB | 머신 readable 요약 (alert 목록 + variable types) |

**열기**: `xdg-open docs/reference/profiling/2026-04-12/bim_objects_enriched.html`
**갱신**: `.venv/bin/python scripts/profile_gold_table.py`

### 5.2 Warehouse Catalog (DBA 관점)

`docs/reference/warehouse-catalog/2026-04-12/`:

| 파일 | 내용 |
|------|------|
| `catalog.md` | 7 tables × storage/columns/sample queries (사람용) |
| `catalog.json` | 219 columns × null/distinct counts (머신용, 86 KB) |

**갱신**: `.venv/bin/python scripts/warehouse_catalog.py`

### 5.3 Lineage Impact Analysis

`docs/reference/lineage/2026-04-12/`:

| 파일 | 내용 |
|------|------|
| `impact-analysis.md` | downstream / upstream 표 (24 datasets × 7 jobs) |
| `lineage-graph.json` | 양방향 인접 리스트 (50 KB) |
| `lineage-graph.dot` | Graphviz DOT (다른 그래프 도구 입력) |
| `lineage-graph.png` | networkx 렌더링 (820 KB, 색상 분류) |

**갱신**: `scripts/emit_lineage.py` → `scripts/trace_lineage.py` (순서 중요)

---

## 6. UI / 외부 도구 캡처 (정리됨)

작업 중 만든 캡처들은 의미별로 적절한 위치로 이동 완료. `temp/` 디렉터리 제거됨.

### 6.1 Foundry Object Type wizard (`docs/reference/foundry-setup-figures/`)

| 파일 | 의미 | 가이드 참조 |
|------|------|-------------|
| `step1-datasource-existing-piping.png` | Step 1 — `Use existing datasource` 선택 ✅ | §5.1 |
| `step3-source-user-input-bug.png` | Step 3 — Source 가 User input 인 버그 ❌ | §5.2 |
| `step3-properties-pk-not-set.png` | Step 3 — PK/Title 미설정 상태 ❌ | §5.3 |

→ [`docs/reference/foundry-setup-guide.md §5`](reference/foundry-setup-guide.md) 부록에 인라인 표시.

### 6.2 Medallion Data Flow baseline (`docs/analysis/medallion-data-flow-figures/`)

| 파일 | 의미 |
|------|------|
| `before-fix-2026-04-14.png` | Figma 수정 전 5개 issue 가 보이는 baseline |

→ [`docs/analysis/medallion-data-flow-review.md`](analysis/medallion-data-flow-review.md) 본문 상단에 인라인 표시.

---

## 7. 부재 / 향후 추가 후보

다음 시각화는 아직 없거나 보강이 필요:

| 항목 | 현재 상태 | 제안 |
|------|-----------|------|
| OWL TBox class hierarchy | `portfolio/architecture-diagrams.html` 의 1 section 만 존재 | rdflib + networkx 또는 protégé 스크린샷 |
| SHACL violations 상세 | 없음 (테스트 결과만) | violation severity × shape × class 히트맵 |
| Foundry Object Type / Link Type 다이어그램 | Foundry UI 캡처만 (`temp/`) | Foundry 내장 lineage view 캡처 또는 ER 다이어그램 |
| Streamlit UI 스크린샷 | Phase 7 미완 → 없음 | Phase 7 완료 후 6 페이지 캡처 |
| Architecture comparison (현 vs 목표) | 없음 | dev-standards R10 후보 (A/B 비교) |

---

## 8. 갱신 / 재생성 절차

```bash
# 모든 분석 시각화 (notebooks/figures/)
.venv/bin/jupyter nbconvert --execute --inplace notebooks/*.ipynb

# Profile 리포트
.venv/bin/python scripts/profile_gold_table.py

# Warehouse 카탈로그
.venv/bin/python scripts/warehouse_catalog.py

# Lineage (순서 중요)
.venv/bin/python scripts/emit_lineage.py
.venv/bin/python scripts/trace_lineage.py

# Power BI mockup pages
.venv/bin/python scripts/powerbi_mockup.py    # 존재 시
```

---

## 9. 디렉터리 구조 요약

```
docs/
├── analysis/
│   ├── medallion-data-flow-review.md         (검토 + 적용 기록)
│   └── powerbi-dashboard-preview/
│       ├── README.md
│       └── figures/  (7 PNG)
├── findings/
│   └── 2026-04-12-M1-piping-misclassification/
│       ├── audit.py · make_figures.py
│       ├── data/      (5 CSV evidence)
│       └── figures/   (4 PNG)
├── reference/
│   ├── lineage/2026-04-12/        (PNG + DOT + JSON + MD)
│   ├── profiling/2026-04-12/      (2 HTML + JSON)
│   └── warehouse-catalog/2026-04-12/ (MD + JSON)
└── VISUALIZATIONS.md              (이 문서 — 통합 인덱스)

notebooks/
├── 01_eda.ipynb               (7 figures)
├── 02_construction_management.ipynb (5)
├── 03_adjacency_tiers.ipynb   (4)
├── 04_construction_schedule.ipynb (4)
├── 05_kpi_dashboard.ipynb     (5)
└── figures/  (25 PNG, DPI 300)

portfolio/
└── architecture-diagrams.html  (Toss-style 8-section page)

temp/                            (정리 대상 — Foundry 캡처 + Figma 백업)
```

---

*Last updated: 2026-04-14*
