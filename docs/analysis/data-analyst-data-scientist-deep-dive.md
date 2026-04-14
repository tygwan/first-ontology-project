# Data Analyst / Data Scientist 관점 심층 분석

> 이 문서는 BIM Knowledge Graph Pipeline 프로젝트를 **Data Analyst**
> 와 **Data Scientist** 두 시선으로 철저히 재검토한 결과입니다.
> 엔지니어 관점(R11 portfolio, architecture-diagrams.html) 이 이미
> 다룬 아키텍처·파이프라인·운영 이슈와는 구분되며, 이 문서는
> **수치·분포·공식·실험 설계·모델링 가능성** 에 집중합니다.
>
> 작성 기준 스냅샷: `2026-04-12` (DXTnavis v1.4.0 PR #3 적용)
> 코드 경로는 모두 `/home/taegwan-dev/dev/first-ontology-project` 기준

---

## 0. Executive Summary (TL;DR)

| 질문 | 이 프로젝트의 답 |
|------|-----------------|
| 데이터 규모는? | 12,009 객체 × 219 Gold 컬럼 + 220,346 인접 엣지 + 477K RDF 트리플 |
| 데이터 품질은? | HIGH 신뢰 2,926 / LIKELY_BUG 136 + SHACL 6 shape 468 위반 자동 탐지 |
| 지표 체계는? | 4 계층 × 33 KPI (criticality, accessibility, corrosion, isolation) |
| 의사결정 근거는? | 3건 A/B 검증 + R10 decision validation + Finding archive (M1/M2/M3) |
| 모델링 여지는? | 4개 후보 task (분류 보정, 시공 예측, 이상 탐지, GraphRAG 추천) — feature/label 분석 포함 |

**결론**: 이 프로젝트는 "ML 모델을 학습시키는" 프로젝트가 아니라
"**ML 을 포함한 모든 분석의 입력 레이어를 설계·검증하는**" 프로젝트
입니다. DA 관점에서는 정제된 단일 진실 원천(Gold + OWL + Neo4j) 이
만들어졌고, DS 관점에서는 위 4 task 가 본격 실행 가능한 단계까지
feature·label 구조가 정리되었습니다.

---

## 1. EDA / Data Analyst 관점

### 1.1 Gold 테이블 프로파일 요약

`docs/reference/profiling/2026-04-12/summary.json` (ydata-profiling 4.18
출력) 기준 Gold 12,009 × 219 에서 **270 개 품질 알림** 이 자동 탐지됨.
주요 카테고리:

| 카테고리 | 건수 | 의미 | 대표 예 |
|----------|-----:|------|---------|
| Constant | **31** | 값이 하나뿐 (분석 가치 0) | `sp3d_approval_status`, `sp3d_end_standard`, `sp3d_is_curved`, `sp3d_manufacturer`, `nav_item_hidden`, `is_hidden`, `ingested_at_utc` |
| Missing ≥ 80% | **72** | 거의 비어있음 | `sp3d_iso_sheet_no` (100%), `sp3d_stress_system_no` (100%), `sp3d_composition` (99.3%), `sp3d_diameter` (99.7%), `sp3d_spool` (99.9%) |
| Highly imbalanced | **24** | 한 범주가 ≥ 55% 지배 | `sp3d_commodity_option` (96%), `sp3d_construction_type` (99%), `sp3d_reference` (97%), `nav_geom_triangles` (99%), `is_parent_box` (77%) |
| Highly correlated | 다수 | 다른 컬럼과 ≥ 0.9 상관 | `bbox_min/max_x` ↔ `centroid_x`, `adjacency_count` ↔ `child_count`, `class_raw` ↔ 45 others |
| Skewed (γ₁ ≥ 10) | **4** | 롱테일 분포 | `bbox_volume_m3` (γ₁=67), `dry_weight_kg` (γ₁=26), `adjacency_count` (γ₁=33) |
| Zeros ≥ 25% | **10** | 0 이 대다수 | `child_count` 66.5%, `vertex_count`, `triangle_count`, `adjacency_count` 27.9% |

**해석 — DA 관점**:
- **드롭 대상**: Constant 31 + 100% missing 4 = **최소 35개 컬럼**은
  분석에서 제외 가능. `is_hidden`, `nav_item_hidden`, `sp3d_iso_sheet_no`,
  `sp3d_stress_system_no`, `nav_item_material` 등.
- **연결성 집계 기준**: `adjacency_count` 와 `child_count` 가 71+ 컬럼과
  상관. 이는 "큰 객체는 모든 차원에서 크다" 는 자명한 구조적 패턴.
- **이상치 처리 필요**: `bbox_volume_m3`, `dry_weight_kg` 가 극단 skew —
  log transform 또는 percentile cutoff 이 분석 전 필수.

### 1.2 219 Gold 컬럼의 DA 가치 분류

column_stats(catalog.json) 기반 집계. Gold 파일 크기 76 MB (parquet).

**High-value (분포·상관에서 분석 가치가 있는 컬럼, ~40)**:

| 범주 | 컬럼 예 | 용도 |
|------|---------|------|
| 식별자 | `object_id` (100% unique), `display_name` (70% unique), `system_path` (92% unique) | join, FTS5 full-text |
| 분류 | `refined_class`, `class_raw`, `original_class` | group by, color by |
| 신뢰도 | `classification_confidence`, `classification_confidence_reason` | 품질 필터 |
| 기하 | `centroid_x/y/z`, `bbox_volume_m3`, `bbox_diagonal_m` | 공간 쿼리, 존 생성 |
| 플래그 | `is_container`, `is_analysis_volume`, `is_parent_box`, `graph_participant`, `in_giant_group`, `has_real_mesh` | 분석 포함/제외 |
| 물리량 | `dry_weight_kg`, `wet_weight_kg`, `length_m`, `design_pressure_kpa`, `design_temperature_c` | KPI 입력 |
| 관계 키 | `pipeline`, `pipe_run`, `level`, `material`, `spec_name`, `group_id` | 조인, 차원 |
| 메시 품질 | `mesh_quality`, `vertex_count`, `triangle_count`, `tess_result`, `tess_failure_reason` | 시각화·검증 |

**Medium-value (조건부 유용, ~60)**:
- SP3D 도메인 특수 컬럼 (`sp3d_dry_weight`, `sp3d_pipeline`, `sp3d_material_name`, 등)
- Navisworks metadata (`nav_material_diffuse_r/g/b`, `nav_geom_triangles`, ...)
- Graph 파생 수치 (`group_size`, `group_total_volume`, `group_edge_count`)

**Low-value (결측·상수, ~120)**:
- `sp3d_*` 중 부서별·환경별로 채워지는 필드 (>80% 결측)
- Navisworks internal pointer 필드 (`nav_item_guid`, `nav_item_unit`, ...)
- Legacy/unused: `sp3d_iso_sheet_no`, `sp3d_stress_system_no`, `sp3d_constuction_type` (오타 컬럼)

### 1.3 5 Notebook 의 분석 질문 카탈로그

`notebooks/` 5 개와 `notebooks/figures/` 25 PNG:

| Notebook | 핵심 질문 | 주요 figure |
|----------|-----------|-------------|
| 01_eda.ipynb | 원본과 정제본의 차이, 결측 분포, 공간 배치, 그래프 허브 | `01_s1_column_fill_rate.png` (컬럼별 결측률), `01_s3_spatial_layout.png` (2D 산점도 × class), `01_s5_graph_degree.png` (degree long-tail), `01_s7_quality_suspects.png` (LOW/LIKELY_BUG 요약) |
| 02_construction_management.ipynb | 시공 관리 관점 (중량 맵, 존 비교, Pipeline 분산) | `02_s1_weight_heatmap.png` (50×50 격자 중량), `02_s2_zone_comparison.png` (Grid vs Louvain 4지표 A/B), `02_s3_ab_metrics.png`, `02_s5_zone_class_composition.png` |
| 03_adjacency_tiers.ipynb | AABB 품질 분석, 3-tier 효과, Pipeline 사례 | `03_s1_relation_types.png` (tier 분포), `03_s2_tier_cross_class.png` (tier × class crosstab), `03_s3_ab_precedence.png` (critical chain 88→53→17) |
| 04_construction_schedule.ipynb | 시공 Gantt, 공간 진행, 의존성 행렬 | `04_s1_gantt_chart.png`, `04_s2_spatial_wave.png`, `04_s3_dependency_matrix.png`, `04_s4_critical_path.png` |
| 05_kpi_dashboard.ipynb | Plant/Equipment/Pipeline/Zone KPI 요약 | `05_s1_plant_overview.png` (KPI 카드), `05_s2_equipment_criticality.png` (660 Equipment 분포), `05_s3_accessibility_isolation.png` (산점도), `05_s5_pipeline_kpis.png` |

### 1.4 25 figures × 사용 목적 × audience

| audience | 권장 figure | 이유 |
|----------|-------------|------|
| CM팀 (시공 관리) | 02_s1, 02_s2, 04_s1, 05_s1 | 시공 관점의 중량·존·Gantt |
| 엔지니어 (설계·품질) | 01_s1, 01_s5, 01_s7, 03_s1, 03_s2 | 데이터 품질·그래프·tier 분석 |
| 경영진 (KPI) | 05_s1, 05_s4, 05_s5 | 집계 결과만 |
| 연구자 (방법론) | 02_s3, 03_s3, 03_s4 | A/B 비교 근거 |

---

## 2. Feature Engineering (Silver → Gold)

### 2.1 파생 플래그 카탈로그

Silver → Gold 단계에서 생성된 주요 플래그와 실제 통계. 소스:
`src/bimkg/ingest/clean.py` (L300–L531).

| 플래그 | 정의 | True 건수 | 비율 | 목적 |
|--------|------|----------:|-----:|------|
| `is_container` | `mesh_quality == "skipped_container"` AND `adjacency_count == 0` | 3,353 | 27.9% | 컨테이너/폴더 노드 분리 (Navisworks `Level` 등) |
| `is_bbox_placeholder` | `mesh_quality == "box_placeholder"` | 변동 | ~30% | 실제 mesh 없는 임시 placeholder |
| `is_analysis_volume` | `display_name` contains `{Insulation, Obstruction, Fireproofing, Acoustic} Volume` | 145 | 1.2% | 물리 객체 아닌 해석용 체적 |
| `has_own_geometry` | `has_real_mesh == True` | ~8,000 | ~66% | 실제 메시 소유 (그래프 참여 필요조건) |
| `is_parent_box` | `has_real_mesh == False` AND `bbox_volume_m3 > 36.34 m³` (99th percentile) | 271 | 2.3% | SP3D 조립체 계층 노드 (M3 발견 후 추가) |
| `graph_participant` | NOT (container OR placeholder OR analysis OR parent_box) | 7,840 | 65.3% | 그래프 분석 대상 |
| `in_giant_group` | `group_id == giant_component_id` | 8,626 | 71.8% | 연결된 주 컴포넌트 소속 |

**핵심 통찰**:
- 원본 12,009 객체 중 **약 35%가 "진짜 물리 객체" 가 아님** (container,
  analysis volume, parent box). 이걸 구분하지 않으면 모든 분석이
  왜곡됨. 이 사실을 플래그 6개로 명시화한 것이 이 프로젝트의
  feature engineering 핵심 가치.
- `graph_participant` 가 모든 그래프 계산의 공통 필터 조건. KPI,
  Louvain, precedence DAG 가 전부 이 플래그를 통과한 7,840 개 노드만
  사용.

### 2.2 SI 단위 엔지니어링

SP3D 가 넘겨주는 문자열 물리량(예: `"17 ft  1.48 in"`, `"284.23 lbm"`)
을 Silver 단계에서 SI float 으로 파싱. 소스:
`src/bimkg/ingest/unit_parser.py` + `clean.py` (L350–L385).

| Raw 컬럼 | Gold 컬럼 (SI) | 단위 | 파서 | 테스트 |
|----------|---------------|------|------|-------|
| `sp3d_dry_weight` | `dry_weight_kg` | kg | `parse_weight` | 44 cases |
| `sp3d_wet_weight` | `wet_weight_kg` | kg | `parse_weight` | ✓ |
| `sp3d_length` | `length_m` | m | `parse_length` | ✓ |
| `sp3d_width` | `width_m` | m | `parse_length` | ✓ |
| `sp3d_depth` | `depth_m` | m | `parse_length` | ✓ |
| `sp3d_height` | `height_m` | m | `parse_length` | ✓ |
| `sp3d_bend_radius` | `bend_radius_m` | m | `parse_length` | ✓ |
| `sp3d_design_max_pressure` | `design_pressure_kpa` | kPa | `parse_pressure` | ✓ |
| `sp3d_design_max_temperature` | `design_temperature_c` | °C | `parse_temperature` | ✓ |
| `sp3d_npd` | `npd_end1_m`, `npd_end2_m` | m | `parse_npd_tuple` | ✓ |

**엔지니어링 관점 정리**:
- Imperial→SI 정규화가 **후속 모든 집계의 단위 정합성을 보장**. KPI
  공식이 SI 를 전제로 작성됨.
- `parse_weight("284.23 lbm")` → 128.93 kg 같은 변환을 Oracle 검증
  (`scripts/verify_phase1.py`) 으로 100% 테스트 — 이건 DA 가
  "weight 단위는 어디가 kg 이고 어디가 lbm 인가" 를 고민하지 않아도
  되게 만드는 계약.

### 2.3 Classification Confidence (3-level)

분류 신뢰도 3단계 플래그의 로직. 소스: `src/bimkg/ingest/clean.py`
(L415–L531) — 8 가지 reason enum.

```
HIGH (2,926) = sp3d_pipeline 있음 AND (commodity_code OR spec_name OR npd)
LOW  (1,088) = sp3d_pipeline XOR (commodity_code OR spec_name OR npd)
LIKELY_BUG (136) = 둘 다 없음 (= substring match bug 피해자)
```

`classification_confidence_reason` (enum, 8 값):
1. `pipeline_full_metadata` (HIGH)
2. `pipeline_partial_metadata` (HIGH)
3. `pipeline_no_metadata` (LOW)
4. `metadata_no_pipeline` (LOW)
5. `no_pipeline_no_metadata_piping_rack` (LIKELY_BUG — "Pipe Rack")
6. `no_pipeline_no_metadata_pipe_trench` (LIKELY_BUG — "Pipe Trench")
7. `no_pipeline_no_metadata_pipeline_folder` (LIKELY_BUG — folder 이름)
8. `no_pipeline_no_metadata_tee_substring` (LIKELY_BUG — "steel"→"tee")

**DA/DS 통찰**:
- LIKELY_BUG 136 개는 **작은 레이블된 데이터셋** 역할을 할 수 있음
  (후속 ML 분류 보정 task 의 labeled set).
- `classification_confidence` 컬럼 자체가 ML 모델의 중요한 feature —
  "상류 분류를 믿을 수 있는가" 를 정량화.

---

## 3. 데이터 품질 통계

### 3.1 Oracle 검증 (12,009 / 12,009)

`scripts/verify_phase1.py` 와 `tests/test_ingest/test_xlsx_oracle.py`
에서 **XLSX RefinedExporter 출력** vs **Python 포팅 분류기 출력**
을 1:1 비교. 12,009 행 전체에서 `refined_class` 일치율 100%.

의미: 내부 분류 로직 버그 없이 상류 DXTnavis 와 bit-for-bit 동등한
결과. M1 fix 이후에도 이 제약을 유지한다는 것이 핵심 regression 방지.

### 3.2 SHACL 6 shape × 468 위반

`src/bimkg/validation/shapes.py` (L26–L179) 에 정의된 6 제약:

| Shape | Severity | 제약 | 위반 건수 |
|-------|:-------:|------|----------:|
| PipingMustHavePipeline | ERROR | PipingComponent minCount(belongsToPipeline) = 1 | 68 |
| EquipmentMustHaveName | WARNING | Equipment minCount(displayName) = 1 | ~30 |
| PhysicalMustHaveMesh | WARNING | PhysicalObject hasValue(hasRealMesh=true) | 400 |
| WeightNonNegative | ERROR | PhysicalObject dryWeightKg minInclusive(0.0) | 0 |
| ObjectMustHaveCoords | ERROR | BIMEntity minCount(centroid_x/y/z) = 1 각 | 0 |
| PipingConfidenceCheck | INFO | PipingComponent classificationConfidence required | ~1,200 (INFO 만) |

합 ERROR+WARNING = 468. INFO 는 집계 외.

**DA 관점**:
- ERROR 68 (Piping 중 pipeline 메타 없음) 은 M1 LIKELY_BUG 집단과 겹침.
  즉 SHACL 이 같은 품질 이슈를 두 경로로 검출 (자동화 redundancy).
- WARNING 400 (mesh 없는 PhysicalObject) 은 M3 parent box 와 일치.
  SHACL validation → Finding archive 로 이어지는 **detect→fix 피드백
  루프** 가 작동한 증거.

### 3.3 AABB 인접성 정밀도 35.4%

M2 finding 에서 측정. 측정 방법:
1. AABB 기반 220,346 edge 를 샘플링
2. 샘플 edge 의 두 객체가 **mesh 레벨에서 실제 닿는지** 수동/자동 확인
   (Producer adjacency 와 대조)
3. True positive / (True positive + False positive) = **35.4%**

즉 "AABB 가 겹친다" 는 신호 중 **64.6% 는 실제 접촉이 아님**. 이게
Strong/Medium/Weak 3-tier 도입의 근거.

Adjacency 3-tier 실제 분포 (220,346 edge 총 기준):

| Tier | 조건 | 건수 | 비율 | 용도 |
|------|------|-----:|-----:|------|
| Strong | 실제 mesh 겹침 | 13,422 | 6.1% | precedence DAG, 엄격 분석 |
| Medium | overlap ≤ 0.01 m³ 또는 tolerance 내 proximity | 73,706 | 33.5% | 기본 분석 (KPI, zone) |
| Weak | overlap > 0.01 m³ 또는 neartouch | 133,218 | 60.4% | 폐기 또는 context only |

### 3.4 데이터 품질의 통계적 요약

- **원본 신뢰 구간**: XLSX 12,009 중 997 오분류 → 최대 ~91.7% 신뢰
  (M1 fix 전). M1 fix 후 HIGH 신뢰 경로 = 2,926 / 4,014 Piping = 72.9%.
- **인접성 신뢰**: AABB 정밀도 35.4% → Strong+Medium 채택 시 precision
  을 ~72% (추정, M2 내 A/B 검증으로 critical chain 길이 5배 축소 근거)
  로 향상.
- **그래프 신뢰**: M3 fix 전 max degree 5,161 (parent box 오염 때문)
  → M3 fix 후 max degree 388 로 **92.5% 감소**. 한 노드가 그래프 중심을
  지배하는 구조적 결함이 제거됨.

---

## 4. A/B 실험 설계 (R10 Decision Validation)

R10 규칙을 만족하는 3 건의 A/B 검증. 모두 **실제 구현** → **지표 측정**
→ **의사결정 근거 기록** 의 사이클.

### 4.1 A/B #1 — Grid vs Louvain (시공 존)

**가설**: 격자 기반 존 분할과 그래프 기반 커뮤니티 검출 중
어느 쪽이 실제 시공 관리에 더 유용한가.

**변수**:
- **A**: 15 m 격자 (52 zones 추정, 공간 균등 분할)
- **B**: Louvain(resolution=3.0, seed=42) — 144 zones

**4 개 지표** (소스: `notebooks/02_construction_management.ipynb` +
`src/bimkg/analytics/zones.py`):

| 지표 | A (Grid) | B (Louvain) | 승자 |
|------|---------:|------------:|:----:|
| `n_objects` per zone (std / mean) | 높음 (불균형) | 낮음 (균등) | B |
| `n_equipment` coverage | 일부 zone 0 | 모든 zone ≥ 1 | B |
| `total_weight_kg` std | 극단 | 중간 | B |
| Cross-zone Pipeline 파편화 | 높음 | 낮음 | B |

**선택**: **B (Louvain)**. Pipeline 이 격자 경계를 가로지르는 비현실적
분할을 피할 수 있고, 144 개 zone × 평균 85 객체는 실제 시공 팀이
다루기에 적절한 단위.

**트레이드오프**: resolution 파라미터 민감. resolution=3.0 은
`notebooks/02_s2_zone_comparison.png` 에서 2.0 / 3.0 / 5.0 을 비교한
결과 144 zone 이 가장 해석 가능했음.

### 4.2 A/B #2 — Adjacency Tier

**가설**: AABB 인접성을 품질 단계별로 나누면 시공 순서 시뮬레이션의
현실성이 향상되는가.

**변수** (`src/bimkg/analytics/precedence.py` L56–95 의
`adjacency_tier` 파라미터):

| 시나리오 | 포함 Tier | 엣지 수 | Critical chain |
|----------|-----------|--------:|---------------:|
| All | Strong + Medium + Weak | 220,346 | **88 steps** |
| Strong+Medium (선택) | Strong + Medium | 87,128 | **53 steps** |
| Strong only | Strong | 13,422 | **17 steps** |

**효과 크기**: Strong+Medium 대비 All 은 **+66%** 길이, Strong only
는 **-68%**. 의사결정 rule: 현실성(거짓 인접 감소) 과 포괄성(누락
방지) 의 균형점 = Strong+Medium.

**통계적 해석**:
- All 시나리오가 88 step 이 나오는 이유는 AABB 가짜 인접으로 생긴
  허위 의존성이 체인 길이를 증폭시키기 때문.
- Strong only 17 step 은 그래프가 너무 성겨져 실제 병렬성을
  과소평가. 연결성 누락.
- Strong+Medium 53 step 이 M3 fix 전 후보였고, M3 이후 precedence DAG
  재생성 시 44 step 으로 추가 감소.

### 4.3 A/B #3 — Pre-M3 vs Post-M3 (Parent Box 제거)

**가설**: parent box (계층 노드) 를 그래프에서 제외하면 Louvain 결과
와 precedence 가 실질적 해석 가능성을 회복하는가.

**6 개 지표** (소스:
`docs/findings/2026-04-13-M3-parent-box-contamination/README.md`):

| 지표 | Pre-M3 | Post-M3 | Δ |
|------|-------:|--------:|---|
| Physical nodes | 8,511 | 7,840 | −671 (−7.9%) |
| Adjacency edges (giant comp.) | 145,346 | ~78,000 | −46% |
| Max degree | 5,161 | 388 | −92.5% |
| Louvain zones (res=3.0) | 29 | **144** | +396% |
| Precedence critical chain | 53 | **44** | −17% |
| Cross-zone edge ratio | 매우 낮음 (hub 지배) | 정상 | 정상화 |

**효과 크기**: Max degree 가 거의 한 자릿수 규모로 감소. Zone 해상도
는 5배 상승. 이건 "noise removal 에 의한 signal amplification" 의
전형적 사례.

---

## 5. KPI 방법론 (Data Scientist)

소스: `src/bimkg/analytics/kpi.py` (305 lines).

### 5.1 Object-level (4 공식)

#### 5.1.1 Equipment Criticality — `kpi.py` L22–L48

```
criticality = normalize(degree × unique_pipeline_neighbors)
```

입력: `gold` (필터 `refined_class == "Equipment"`), `adjacency` (join
으로 각 장비의 인접 pipeline 목록 추출).

- `degree`: 각 장비의 인접 객체 수
- `unique_pipeline_neighbors`: 해당 장비에 연결된 고유 pipeline 수
- normalize: min-max → [0, 1]

**해석**: 연결성 많고 여러 pipeline 과 엮여 있을수록 정지 시 영향
크다. 660 Equipment 대상.

#### 5.1.2 Maintenance Accessibility Index — `kpi.py` L51–L76

```
accessibility = 1 / (1 + neighbor_count_within_5m)
```

- `neighbor_count_within_5m`: 3D 유클리드 거리 5m 이내 객체 수
- 값 범위 (0, 1]: 1 에 가까우면 주변이 비어 접근 쉬움, 0 에 가까우면
  밀집.

**해석**: 밀집 구역에서 작업자 접근/공구 회전 공간이 부족한 정도.
KPI 의 물리적 직관이 명확한 대표 사례.

#### 5.1.3 Corrosion Risk — `kpi.py` L79–L108

```
corrosion_risk = normalize(pressure × temperature × material_factor)
```

- `pressure` = `design_pressure_kpa`
- `temperature` = `design_temperature_c`
- `material_factor` = {Carbon Steel: 1.0, Stainless: 0.3, Other: 0.5}

양쪽 다 non-null 인 행(~300 건) 만 계산. 나머지는 `NaN` → zone 집계
에서 평균 계산 시 제외.

**해석**: 운영 조건(압력·온도) 과 재질의 곱으로 부식 잠재성 정량화.
단순 휴리스틱이지만 domain-sensible baseline.

#### 5.1.4 Valve Isolation Analysis — `kpi.py` L111–L169

가장 복잡한 KPI. Piping-only subgraph 에서:

1. **Valve 인식**: display_name 에 `{valve, blind flange, blind,
   spectacle}` 패턴 포함하는 객체 → `is_isolation_valve=True`
2. **Isolation section BFS**:
   - 각 valve 에서 출발
   - 다른 valve 를 만날 때까지 Piping 객체 BFS
   - 도달한 객체 수 = `isolation_section_size`
3. 결과: 각 object 에 `{is_isolation_valve, isolation_section_size}`

**해석**: 특정 valve 를 잠갔을 때 **격리되는 pipe 섹션의 크기**.
그래프 알고리즘이 domain knowledge (valve semantics) 와 결합된 좋은
예.

### 5.2 Zone-level (6 집계)

Louvain 144 zone 에 대해:
- `zone_object_count`, `zone_total_weight_kg`, `zone_equipment_count`
- `zone_mean_corrosion_risk`, `zone_mean_accessibility`
- `zone_critical_equipment_count` (criticality 가 90th percentile 초과인
  Equipment 개수)
- `zone_shutdown_impact` (해당 zone 내 객체가 속한 고유 pipeline 수)

### 5.3 Pipeline-level (7 집계)

147 pipeline × 334 piperun 에 대해:
- `pipeline_object_count`, `pipeline_total_weight_kg`
- `pipeline_mean_pressure_kpa`, `pipeline_mean_temperature_c`
- `pipeline_zone_span` (몇 개 zone 에 걸치는지)
- `pipeline_valve_count`, `pipeline_isolation_sections`
- `pipeline_corrosion_risk` = `normalize(mean_p × mean_t)`

### 5.4 Plant-level (8 집계)

모델 전체 단일 수치:
- `total_objects`, `total_physical_objects`, `total_weight_tonnes`
- `critical_chain_length`, `max_parallel_zones`
- `high_criticality_equipment` (criticality ≥ 0.9 count)
- `high_corrosion_pipelines`, `low_accessibility_zones` (≤ 0.1)

### 5.5 KPI 설계의 DS 관점 비판

- **장점**: 4 계층 aggregation 이 명확히 분리 (object → zone →
  pipeline → plant), 각 지표가 도메인 직관과 대응.
- **한계**:
  - corrosion_risk 가 `material_factor` 3-구분 heuristic — 실제
    부식 모델(예: Arrhenius + pit-depth) 대비 러프.
  - accessibility 가 5m 고정 반경 — ISO/API 기준 (2.5m–3m 통로) 과
    다를 수 있음.
  - criticality 가 graph-structural 만 고려 — 운영 중요도(처리량,
    경제 가치) 는 미반영.
- **개선 여지 (향후 ML)**: 실제 유지보수 이력이 있다면 corrosion_risk
  를 regression target 으로 학습 가능.

---

## 6. OWL 온톨로지 + SHACL 통계

### 6.1 Class Hierarchy (28 classes)

`src/bimkg/ontology/schema.py` L52–L79 의 실제 트리:

```
BIMEntity
├── BIMObject
│   ├── PhysicalObject
│   │   ├── PipingComponent
│   │   ├── StructuralMember
│   │   ├── Equipment
│   │   │   ├── ProcessEquipment
│   │   │   ├── ElectricalEquipment
│   │   │   ├── ArchitecturalEquipment
│   │   │   ├── HvacEquipment
│   │   │   ├── CivilElements
│   │   │   ├── CivilEquipment
│   │   │   ├── BlackBoxSystems
│   │   │   └── UnclassifiedEquipment
│   │   ├── ElectricalComponent
│   │   ├── HvacComponent
│   │   └── UncategorizedObject
│   └── Container
│       └── HierarchyNode
├── Context   (Individuals: Pipeline, PipeRun, Level, Material, Spec)
└── AnalysisArtifact
    └── AnalysisVolume
```

계층 설계 원칙 (D1–D9 결정 기록에 남김):
- **Sibling** 구조 (BIMObject ∥ AnalysisArtifact) — 물리 객체와 분석
  artifact 를 하나의 공통 부모 아래 두지 않음.
- Equipment 만 하위 8 subclass 세분화 (타 클래스는 flat).
- Context 는 instance 만 있고 subclass 는 없음 (Pipeline 같은 공유
  개체).

### 6.2 Properties (8 + 32)

**8 Object Properties** (domain → range):

| Property | Domain | Range | Characteristic |
|----------|--------|-------|---------------|
| adjacentTo | BIMObject | BIMObject | Symmetric |
| hasParent | BIMObject | BIMObject | — |
| belongsToPipeline | PipingComponent | Pipeline | — |
| belongsToPipeRun | PipingComponent | PipeRun | — |
| hasMaterial | PhysicalObject | Material | — |
| hasSpecification | PhysicalObject | Specification | — |
| atLevel | BIMObject | Level | — |
| inGroup | BIMObject | ConnectedGroup | — |

**32 Data Properties** (XSD types):
- string: `objectId`, `displayName`, `refinedClass`, `classRaw`,
  `classificationConfidence`, `classificationConfidenceReason`,
  `commodityCode`, `npd`, `specName`, `constructionType`, `meshQuality`
  등
- double: `centroidX/Y/Z`, `bboxVolumeM3`, `bboxDiagonalM`,
  `dryWeightKg`, `wetWeightKg`, `lengthM`, `widthM`, `depthM`,
  `heightM`, `designPressureKpa`, `designTemperatureC`
- integer: `vertexCount`, `triangleCount`, `adjacencyCount`,
  `childCount`, `groupSize`
- boolean: `hasRealMesh`, `isContainer`, `isAnalysisVolume`,
  `isParentBox`, `graphParticipant`, `inGiantGroup`

### 6.3 ABox 생성 통계

- **Class assertion triples**: 12,009 (객체당 1 개)
- **Data property triples**: ~300K (객체당 25 평균)
- **Object property triples**: ~165K (인접 + 계층 + pipeline 등)
- **총 RDF 트리플**: **477,000+**
- 파일: `bim-objects.ttl` 13 MB + `bim-spatial.ttl` 12 MB +
  `bim-shared.ttl` 0.1 MB

**공유 개체 (505)** — ABox 크기 최적화:
- Pipeline: 147 개 (unique URI), 각 pipeline 은 여러 PipingComponent
  의 object property target 으로 재사용
- PipeRun: 334, Level: 10, Material: 4, Spec: 10

### 6.4 OWL RL 추론 효과 (owlrl)

추론 전 triples: 477K. OWL RL 추론 (소스: 가능하면 SHACL + reasoning
단계) 적용 시 **추가 triples 약 ~50K** (symmetric closure of adjacentTo,
rdfs:subClassOf transitive 등) 예상. 실제 수치는 추후 `reasoner.py`
실행 결과로 확인 필요.

### 6.5 SHACL 위반 분포 분석

`src/bimkg/validation/shapes.py` + pySHACL 실행 결과:

| Shape | ERROR | WARNING | INFO | 총 |
|-------|------:|--------:|-----:|---:|
| PipingMustHavePipeline | 68 | 0 | 0 | 68 |
| EquipmentMustHaveName | 0 | ~30 | 0 | 30 |
| PhysicalMustHaveMesh | 0 | 400 | 0 | 400 |
| WeightNonNegative | 0 | 0 | 0 | 0 |
| ObjectMustHaveCoords | 0 | 0 | 0 | 0 |
| PipingConfidenceCheck | 0 | 0 | ~1200 | (INFO) |

**DS 통찰**:
- **ERROR 68 = M1 LIKELY_BUG 136 의 subset** — SHACL 이 품질 이슈를
  두 경로(pipeline 메타 없음) 중 하나로 검출.
- WARNING 400 = M3 parent box 271 + 기타 mesh 없는 Container ~130 조합.
  SHACL validation → Finding archive 피드백 루프가 검증됨.

---

## 7. 그래프 통계 & 분석 가능성

### 7.1 Graph Centrality Metrics

`src/bimkg/analytics/metrics.py` L44–L53:
```python
degree_centrality = nx.degree_centrality(G)
clustering_coefficient = nx.clustering(G)
```

그래프 G: `graph_participant == True` 인 7,840 node × Strong+Medium
87,128 edge.

### 7.2 Louvain 파라미터 결정

`src/bimkg/analytics/zones.py` L25–L36: `resolution=3.0, seed=42`.

선정 근거 (`notebooks/02_construction_management.ipynb` 내 비교):

| resolution | Zones | 평균 zone 크기 | 해석 |
|-----------:|------:|--------------:|------|
| 1.0 | ~30 | ~260 객체 | 너무 큰 덩어리, zone 간 구분 약함 |
| 2.0 | ~70 | ~112 | 중간, 일부 zone 이 크로스-pipeline |
| **3.0 (선택)** | **144** | **~55** | 시공 팀 단위 적절, pipeline 보존 |
| 5.0 | ~220 | ~36 | 너무 작음, 단일 equipment 과잉 분해 |

### 7.3 Precedence DAG (18,214 edges)

`src/bimkg/analytics/precedence.py` L56–L95.

**Edge 생성 규칙 3 종**:
1. **class_order**: `INSTALL_ORDER = {Equipment:0, Structure:1,
   Piping:2, Electrical:3, HVAC:4, Other:5}` 의 역순 — 먼저 설치할
   것이 나중 설치 대상에 선행.
2. **vertical**: Z 축 bin (`VERTICAL_BIN_M = 3.0`) 기준 낮은 층 →
   높은 층 (구조물 선설치 원칙).
3. **adjacency_interference**: 같은 zone 내 Strong+Medium 인접 edge
   를 기반으로 공간 간섭 의존성.

**DAG 결과**:
- Total edges: 18,214
- Critical chain (longest path): **44 steps** (post-M3)
- Max parallel paths: 미측정 (향후 분석 가능)

### 7.4 ZONE_PRECEDES (zone-level)

144 zone 간의 메타 precedence: zone A → zone B 가 "A 의 다수 객체가
B 의 다수 객체보다 먼저 설치" 라는 집계 규칙. Neo4j 에서 6 번째
relationship type 으로 노출.

---

## 8. ML / 추론 가능성 (Data Scientist 관점의 확장)

이 프로젝트는 **ML 을 구현하지 않았지만**, 지금 구조 위에서 4 개 task
가 즉시 실행 가능. 각 task 의 feature/label 구조를 정리.

### 8.1 Task A — 미분류 객체 자동 분류 (LIKELY_BUG 보정)

**문제 정의**: LIKELY_BUG 플래그된 136 건을 어느 진짜 class 로
재분류할지 예측.

**Labeled set** (supervised learning 가능):
- HIGH 신뢰 2,926 건 중 무작위 1,000 건을 test, 나머지 1,926 건을 train
- LIKELY_BUG 136 건은 predict-only

**Features** (39 개 후보):
- Text: `display_name` (word embedding or TF-IDF), `system_path`
- Categorical: `sp3d_*` metadata (`commodity_code`, `material_name`,
  `spec_name`, `npd`)
- Numeric: `bbox_volume_m3`, `dry_weight_kg`, `centroid_z`,
  `adjacency_count`, `vertex_count`
- Graph: 이웃 객체의 `refined_class` majority

**Label**: `refined_class` (7 범주)

**난이도**: 중 (text + categorical + graph feature — gradient boosting
or graph neural network)

**예상 성능**: HIGH 신뢰 데이터만으로 train 시 accuracy ≥ 0.95 예상.
LIKELY_BUG 의 ~60-80% 를 confident 하게 재분류 가능할 것.

### 8.2 Task B — 시공 시간 예측

**문제 정의**: 각 zone 또는 각 critical step 의 완료 시간을 예측.

**Labeled set**: **외부 데이터 필요** — 실제 historical 시공 완료
기록. 프로젝트 내부에는 ground truth 없음.

**Features**:
- Zone-level: `zone_object_count`, `zone_total_weight_kg`,
  `zone_equipment_count`, `zone_mean_accessibility`
- Step-level: `step_index` (1-44), `classes_involved`, `parallel_zones`
- Dependency: `predecessor_count`, `successor_count`

**Label**: 시공 소요 시간 (days)

**난이도**: 상 (ground truth 확보 필요, domain expert labeling 비용)

**대안**: Simulation-based labeling — 표준 공수 계수 (예: PipingComponent
1 개당 2 hr) 로 합성 label 생성 후 regression.

### 8.3 Task C — 이상 탐지 (Statistical Anomaly)

**문제 정의**: SHACL 위반 외에 통계적으로 이상한 객체 탐지.

**Approach**:
1. **Univariate outliers**: IQR 또는 z-score 로 각 numeric 컬럼 극단값
   탐지.
2. **Multivariate**: Isolation Forest on {bbox_volume, weight, degree,
   centroid_z} — 다차원 이상 조합 (예: "작은 bbox 지만 degree 5000" —
   실제로 M3 parent box 와 같은 패턴).
3. **Graph anomaly**: degree_centrality + clustering_coefficient 의 joint
   distribution 에서 outlier.

**Labeled set**: 비지도 (unsupervised) — 후속 expert 검수 필요.

**난이도**: 중. Isolation Forest + UMAP 시각화로 baseline 가능.

**예상 발견**: M3 와 유사한 구조적 오류, 잘못 extracted mesh, 잘못
레이블된 Equipment 의 subclass 등.

### 8.4 Task D — GraphRAG 유사 설비 추천

**문제 정의**: "이 Equipment 와 설계·운영 조건이 비슷한 다른 Equipment
는?" 에 답.

**Approach**:
1. **Node embedding**: node2vec 또는 GraphSAGE 를 Neo4j graph
   (261K edge) 에 적용.
2. **Feature augmentation**: node embedding + `{refined_class,
   dry_weight_kg, design_pressure_kpa, design_temperature_c, material}`
   concatenate.
3. **KNN** on 660 Equipment 으로 유사 검색.

**Labeled set**: 없음 (self-supervised graph embedding + feature
similarity).

**난이도**: 중. LangGraph agent 의 "Cypher Tool" 이 이미 path finding
을 지원하므로 초기 version 은 Cypher query 로 baseline 가능.

**Business value**: 유지보수 시 "이 pump 와 유사 spec pump 의 과거
이력 조회" 같은 건설 관리 팀 workflow.

### 8.5 4 task 비교표

| Task | 난이도 | Labeled data? | 예상 ROI | 우선순위 |
|------|:-----:|:-------------:|---------|:-------:|
| A. 분류 보정 | 중 | O (HIGH 2,926) | 즉시 M1 잔여 fix | 1 |
| D. GraphRAG 추천 | 중 | 불필요 (self-sup) | Agent 품질 상승 | 2 |
| C. 이상 탐지 | 중 | 불필요 | 품질 피드백 루프 | 3 |
| B. 시공 시간 예측 | 상 | 외부 필요 | 운영 가치 가장 큰 | 4 |

---

## 9. Findings & 통계적 의사결정

Finding archive (`docs/findings/`) 의 3 건 이슈는 모두 **통계적 증거
수집 → 영향 분석 → 해결 → 재검증** 사이클을 통과.

### 9.1 M1 — Piping Misclassification (2026-04-12)

**Audit 결과** (`docs/findings/2026-04-12-M1-piping-misclassification/`):
- `audit.py` 가 생성한 5 CSV evidence:
  - `piping_confidence_breakdown.csv`: HIGH/LOW/LIKELY_BUG count
  - `substring_bug_causes.csv`: bug 원인 키워드 분포 (pipe→Pipe Rack
    770, steel→tee 10, 기타 356)
  - `likely_misclassified_sample.csv`: 136 건의 sample view
  - `keyword_hit_debug.csv`: InferClass 가 어느 keyword 에서 false
    positive 를 냈는지
  - `structure_sanity_check.csv`: 구조물과 Piping 의 공간 분포 비교
- `make_figures.py` → 4 PNG (confidence 분포, bug 원인, 오분류 샘플,
  class 분포)

**통계적 의사결정**:
- Piping 오분류율 24.8% 는 "수용 불가" 임계 (일반적 data quality
  threshold 5% 보다 훨씬 높음).
- Negative lookahead regex 도입 → 재현성 100% (Oracle 검증).
- LIKELY_BUG 136 건은 잔여 uncertainty 로 명시 (0 이 아님).

### 9.2 M2 — Adjacency Tier (2026-04-12)

**Audit 방식**: AABB sampling → mesh-level 대조 → precision 35.4%
계산. 재현 스크립트: `docs/findings/2026-04-12-M2-adjacency-tiers/`.

**통계적 의사결정**:
- "정밀도 35.4%" 는 이진 결정 기준에 미달 (일반적으로 80%+ 기대).
- 따라서 binary (인접/비인접) 대신 **ordinal tier** 로 전환.
- critical chain 길이 A/B (88/53/17) 로 **Strong+Medium 을 채택 하는
  것이 단일 best** 임을 보임.

### 9.3 M3 — Parent Box Contamination (2026-04-13)

**Audit 방식**: max degree 분포 탐색 → outlier (degree 5,161)
드릴다운 → parent box 정체 확인. 관련 finding dir:
`docs/findings/2026-04-13-M3-parent-box-contamination/`.

**통계적 의사결정**:
- Power-law degree distribution 의 tail (degree > 1,000) 이 모두 271
  개 parent box 에 집중.
- Exclusion 후 그래프 통계 정규화 (max degree 388, mean ~22).
- Zone count 29 → 144 로 **해상도 5x 향상** = noise 제거의 signal
  amplification 효과.

### 9.4 Phase 1 Verification Findings

`docs/analysis/phase-1-verification-findings.md` 의 추가 발견:
- Equipment 153 건의 name 누락 (이후 sp3d_equipment_name 패턴
  매칭으로 복구).
- SourceFileName 0.008% → ~100% 복구 (raw_properties_json 재파싱).
- 36 건 constructionType 좌표 오염 (NULL 처리).

---

## 10. 종합 — DA/DS 관점의 프로젝트 가치

### 10.1 이 프로젝트가 DA 에게 제공하는 것

1. **단일 진실 원천** (Gold Parquet + SQLite + OWL + Neo4j) — 하나의
   데이터 정제본을 여러 도구에서 동일한 의미로 질의 가능.
2. **품질 게이트** (3-level confidence + 6 SHACL shapes) — 분석 전에
   필터 조건이 명시화됨.
3. **Feature engineered flags** — `is_container`, `is_parent_box`,
   `graph_participant` 등 6 개 플래그로 복잡한 객체 분류를 한 번에
   필터링.
4. **KPI 카탈로그** — 33 KPI × 4 계층 이 미리 계산되어 대시보드 /
   BI 도구에 바로 연결 가능.
5. **A/B 비교 원본** — 3 건 검증 표가 노트북에 남아있어 후속 분석이
   의사결정 근거를 그대로 재사용 가능.

### 10.2 이 프로젝트가 DS 에게 제공하는 것

1. **Labeled 데이터셋 potential** — HIGH 신뢰 2,926 건 이 supervised
   분류 task 의 train 후보.
2. **Graph embedding ready** — Neo4j 7,840 node × 87K edge 가
   node2vec/GraphSAGE 입력으로 즉시 활용 가능.
3. **Feature store semantic** — 28 OWL class + 32 data property 가
   "어느 feature 가 어떤 의미를 가지는가" 를 FlagSet 기반으로 정리.
4. **Anomaly detection base** — SHACL 위반 468 건 + M3 발견이 supervised
   anomaly detection 의 seed label 로 작용 가능.
5. **Hypothesis testing framework** — R10 A/B 패턴이 내재화되어
   새로운 분석 질문마다 "지표 두 개 비교" 의사결정 절차가 복제 가능.

### 10.3 한계 & 향후 확장

- **외부 ground truth 부재**: 시공 시간·실제 운영 이력이 없으므로
  Task B (시공 시간 예측) 는 simulation-based 또는 외부 데이터 연동
  필요.
- **도메인 전문가 루프 부재**: corrosion, accessibility 지표의
  계수(`material_factor`, 5m 반경) 는 엔지니어링 룸 피드백으로 재조정
  필요.
- **Feature drift 모니터링 미구축**: snapshot 1건 분석만 존재.
  2026-05-XX 등 다음 snapshot 이 오면 Gold 테이블 delta 분석 + KPI
  재계산 절차가 자동화되어야.
- **Interactive exploration 부재**: Phase 7 (Streamlit UI) 가 Phase
  0-6 완료 후 pending. BI 도구 또는 Jupyter widget 으로 DA 의
  ad-hoc query 가능한 표면이 필요.

---

## 11. 참조

- Gold table: `data/enriched/2026-04-12/bim_objects_enriched.parquet`
- Profiling: `docs/reference/profiling/2026-04-12/summary.json` (270 alerts)
- Warehouse catalog: `docs/reference/warehouse-catalog/2026-04-12/catalog.md`
- KPI 공식: `src/bimkg/analytics/kpi.py`
- Feature engineering: `src/bimkg/ingest/clean.py`
- SHACL shapes: `src/bimkg/validation/shapes.py`
- OWL schema: `src/bimkg/ontology/schema.py`
- Louvain zones: `src/bimkg/analytics/zones.py`
- Precedence DAG: `src/bimkg/analytics/precedence.py`
- A/B 검증 노트북: `notebooks/02_construction_management.ipynb`,
  `notebooks/03_adjacency_tiers.ipynb`
- Finding archives: `docs/findings/2026-04-12-M1-*`,
  `docs/findings/2026-04-12-M2-*`, `docs/findings/2026-04-13-M3-*`
- PROJECT-JOURNAL 포털: `docs/PROJECT-JOURNAL.md`

---

*Last updated: 2026-04-14*
