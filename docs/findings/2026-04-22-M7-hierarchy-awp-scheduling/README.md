# 2026-04-22 — M7 — Hierarchy-based AWP Scheduling: 12,009 objects with temporal dimension

**Severity**: 🟡 ENHANCEMENT (ontology gap — no temporal coverage)
**Status**: 🔄 Implementation in progress (DXTnavis PR #5 + schedule builder)
**Discovered by**: DXTnavis Dynamic Schedule v2.0 all-object scheduling analysis
**Affects**: Container/HierarchyNode modeling, temporal scheduling, AWP work packaging

> ⚠️ **2026-04-22 Audit Update**: This README was originally drafted from DXTnavis-side
> reasoning and contained several **unverified estimates**. A subsequent reproducible
> audit (`audit.py`) against the Gold parquet revealed:
>
> - 6/7 coverage numbers exact (12,009 / 7,890 / 2,926 / 4,964 / 4,119) ✓
> - Eqp Type 0: claimed `~300` → actual **153** (-49%)
> - Non-pipeline class breakdown estimates wrong by **70-130%** (see §6)
> - "Level 2 = Area" hypothesis (§1.1) **breaks**: 98.8% of objects sit under a single
>   Level-2 node ("TRAINING"). Real Areas live at depth 3-5.
> - "~677 task" projection (§1.3) NOT reproducible at any prefix depth
>
> **Structural conclusions remain valid** (24% Pipeline-only coverage gap is real,
> hierarchy fallback is a sensible direction); the **specific numerical projections
> need revision**. See §6 Audit & Evidence for full breakdown and corrected values.

---

## 1. Finding

### 1.1 Hierarchy encodes AWP structure

Navisworks 모델 계층(Level 0–9)이 **자연스러운 AWP(Advanced Work Packaging) 구조**를 인코딩하고 있습니다.
현재 온톨로지의 `HierarchyNode`는 순수 containment로만 모델링되어 있지만,
실제 데이터에서 **Area / Unit / Discipline 분리 가능한 계층 구조**가 존재합니다.

> ⚠️ **Audit caveat (§6)**: 원래 본문은 "Level 2 = Area, Level 3 = Unit, Level 4 = Discipline"
> 으로 단순 매핑을 가정했으나, audit 결과 **system_path 의 segs[1] (= 진짜 Level 2) 은
> 4개 노드만 존재하고 'TRAINING' 단일 노드가 11,860/12,009 (98.8%) 를 점유**합니다.
> 실제 AWP-style Area 노드 (A2, Refining Area, Sulphur Recovery Area 등) 는 depth 3-5 에
> 위치하므로, hierarchy fallback 구현 시 단순 `level == N` 매칭이 아닌 **path 패턴 기반
> 추출 로직** 필요.

```
Level 0: File (dxtnavis_test.nwf)
Level 1: Model (Aveva_E3D_MFTEST.nwd)
Level 2: Area (A2, Training Sulphur Recovery, Electrical Substation, ...)
Level 3: Unit (/A2/B01, /A2/Equipment, /TSR/B01, ...)
Level 4: Discipline (Piping, Equipment, Structure, CableTray, ...)
Level 5-9: Component hierarchy (individual objects)
```

### 1.2 Piping-only coverage gap

현재 DXTnavis의 Pipeline 4D 스케줄러는 SP3D `Pipeline`/`PipeRun` 속성이 있는 객체만 그룹핑합니다.

| 범위 | 객체 수 | 비율 |
|------|---------|------|
| 전체 모델 | 12,009 | 100% |
| SP3D Geometry Group (물리 객체) | 7,890 | 65.7% |
| Pipeline 속성 보유 (Piping) | 2,926 | 24.4% |
| Pipeline 없는 SP3D 객체 | 4,964 | 41.3% |
| Navisworks-only (비물리) | 4,119 | 34.3% |

**4,964개의 비배관 SP3D 객체**가 스케줄에서 누락됩니다 (refined_class 기준 audit 검증):

| refined_class | 원래 추정 | **audit 실측** | 차이 |
|---|---:|---:|---:|
| Structure (StructuralMember 외) | ~1,200 | **2,577** | +115% |
| Electrical (CableTray 외) | ~400 | **792** | +98% |
| Equipment (ProcessEquipment 외) | ~300 | **697** | +132% |
| Other (HgrProfile, Insulation 외) | ~3,000 | **830** | -72% |
| HVAC | (위 "기타" 에 포함) | **68** | — |
| **합계** | ~4,900 | **4,964** | ✓ 합계는 일치 |

→ 합계(4,964) 는 정확하나, *세부 분포* 는 7번째 hallucination 사례 (M1, M5, M6, A1, A3-A8 시리즈와 같은 부류). audit script 가 산출한 값 사용 권장. CSV 증거: [`data/non_pipeline_class_breakdown.csv`](data/non_pipeline_class_breakdown.csv)

### 1.3 Hierarchy fallback으로 전체 커버리지 달성

계층 ancestor 이름을 fallback slot 값으로 사용하면 **12,009개 전체 객체**를 AWP 구조로 그룹핑할 수 있습니다.

**Pipeline-only vs Hierarchy fallback** (audit 실측, [`data/task_count_simulation.csv`](data/task_count_simulation.csv)):

| Strategy | grouping key | n_tasks | 커버 객체 | 비율 |
|---|---|---:|---:|---:|
| Pipeline-only (현재 DXTnavis) | (sp3d_pipeline, sp3d_pipe_run) | **378** | 2,926 | 24.4% |
| Hierarchy prefix depth 2 | system_path[:2] | 5 | 12,009 | 100% |
| Hierarchy prefix depth 3 | system_path[:3] | 149 | 12,009 | 100% |
| Hierarchy prefix depth 4 | system_path[:4] | 183 | 12,009 | 100% |
| Hierarchy prefix depth 5 | system_path[:5] | 299 | 12,009 | 100% |
| Hierarchy prefix depth 6 | system_path[:6] | 938 | 12,009 | 100% |
| Hierarchy prefix depth 7 | system_path[:7] | 4,242 | 12,009 | 100% |

> ⚠️ **원래 README 의 "예상 ~677 task" 추정치는 어떤 prefix depth 에서도 재현 안 됨**.
> ~677 은 depth-5 (299) 와 depth-6 (938) 사이에 위치하지만, 어떤 principled cutoff 에도 해당하지 않음.
> **권장 grouping**: AWP 의 "task 적정 크기" 정책에 따라 depth 4-5 (183-299 task) 가 합리적.

### 1.4 시간 차원 — 스케줄 자동 생성

**이것이 온톨로지 프로젝트에 가장 큰 영향을 미치는 발견입니다.**

현재 온톨로지(28 classes, 477K triples)는 **공간/분류/관계** 정보만 포함하고 있으며,
**시간(temporal) 차원이 완전히 부재**합니다.

DXTnavis Dynamic Schedule Builder v2.0은 다음을 자동 생성할 수 있습니다:

```
각 객체 그룹 → {TaskName, PlannedStart, PlannedEnd, Duration, TaskType, ObjectIds}
```

**시간 매핑 전략**:
- `Hybrid`: duration = BaseDurationHours + (ObjectCount x HoursPerObject)
- `FixedDuration`: 고정 기간
- `ObjectCountBased`: 객체 수 비례

**공간 정렬** (시공 순서 결정):
- `NearestNeighbor`: BBox 기준점에서 가장 가까운 그룹부터 순차 방문 (greedy)
- `SpatialLeftToRight`: PCA 기반 공간축 투영

이 시간 데이터를 온톨로지에 통합하면:
1. **4D BIM** — 공간 + 시간 통합 시뮬레이션
2. **AWP 최적화** — Area/Unit/Discipline 기반 작업 패키지 자동 생성
3. **시공 순서 추론** — 공간 근접성 기반 시공 시퀀스 추론
4. **일정 충돌 감지** — 동일 공간/시간대 작업 간 간섭 분석

---

## 2. Evidence

### 2.1 계층 구조 매핑 (실제 데이터)

```
A2/                                    <- Level 2: Area
+-- B01/                               <- Level 3: Unit
|   +-- Piping/                        <- Level 4: Discipline
|   |   +-- Pipeline P-015/            <- Level 5: Pipeline
|   |   |   +-- PipeRun Dist.Unit/     <- Level 6: PipeRun
|   |   |       +-- [Geometry Group]   <- Level 7-9: Components
|   |   +-- Pipeline P-022/
|   +-- Equipment/
|   |   +-- [Pump, Vessel, ...]
|   +-- Structure/
|       +-- [MemberPartPrismatic, ...]
+-- Equipment/                         <- Level 3: Unit (equipment area)
|   +-- [ProcessEquipment, ...]
Training Sulphur Recovery/             <- Level 2: Area
+-- B01/
|   +-- Piping/
|   +-- Structure/
Electrical Substation/                 <- Level 2: Area
+-- ...
```

### 2.2 SP3D 속성 커버리지

| 속성 | 보유 객체 | 전체 대비 |
|------|----------|----------|
| `SP3D\|Name` | 7,890 / 12,009 | 65.7% (= Geometry Group 전체) |
| `SP3D\|Pipeline` | 2,926 / 12,009 | 24.4% (배관만) |
| `SP3D\|PipeRun` | 2,926 / 12,009 | 24.4% (배관만) |
| `SP3D\|Eqp Type 0` | **153** / 12,009 | **1.3%** (audit 정정, README 원본 ~300/~2.5% 는 -49% 오차) |
| `Item\|Type` | 7,890 / 12,009 | 65.7% (= SP3D\|Name과 동일 범위) |

### 2.3 비배관 객체 분류 (4,964개)

> Audit 검증된 refined_class 분포는 §1.2 표 참조 (Structure 2,577 / Electrical 792 /
> Equipment 697 / Other 830 / HVAC 68). 아래 표는 **원본 추정 + display_name 매핑** 으로
> 보존하되 *실측* 컬럼 추가:

| refined_class | 대표 display_name | 원래 추정 | **audit 실측** |
|---|---|---:|---:|
| `Structure` (StructuralMember) | MemberPartPrismatic, MemberSystem | ~1,200 | **2,577** |
| `Electrical` (ElectricalComponent) | CableTray, Cableway, Cable Tray Part | ~400 | **792** |
| `Equipment` 하위 | ProcessEquipment, CivilElements | ~300 | **697** |
| `Other` (UncategorizedObject) | HgrProfile, Cover, Insulation | ~3,000 | **830** |
| `HVAC` | Duct, Diffuser 등 | (위 "기타"에 포함) | **68** |

### 2.4 스케줄 자동 생성 예시 (NearestNeighbor + BBoxMin)

```csv
TaskName,PlannedStart,PlannedEnd,TaskType,ObjectCount,GroupKey
A2/B01/Piping/P-015,2026-06-01,2026-06-05,Construct,45,A2|B01|Piping
A2/B01/Piping/P-022,2026-06-05,2026-06-08,Construct,28,A2|B01|Piping
A2/B01/Structure,2026-06-08,2026-06-15,Construct,180,A2|B01|Structure
A2/B01/Equipment,2026-06-15,2026-06-17,Construct,12,A2|B01|Equipment
A2/Equipment/ProcessEqp,2026-06-17,2026-06-19,Construct,8,A2|Equipment|ProcessEqp
TSR/B01/Piping/P-031,2026-06-19,2026-06-22,Construct,33,TSR|B01|Piping
...
```

---

## 3. Analysis

### 3.1 온톨로지 영향

**현재 스키마에서 관련 클래스**:

```
Container > HierarchyNode    -- 계층 노드 (Area, Unit 등)
Context > Level              -- 현재는 건물 층 개념만
```

**제안: 시간 차원 확장**

```turtle
# Option A: ScheduleTask as new class
bim:ScheduleTask  rdfs:subClassOf  bim:AnalysisArtifact .
bim:hasSchedule   rdf:type         owl:ObjectProperty ;
                  rdfs:domain      bim:PhysicalObject ;
                  rdfs:range       bim:ScheduleTask .

# Option B: Data properties on existing PhysicalObject
bim:plannedStart  rdf:type    owl:DatatypeProperty ;
                  rdfs:domain bim:PhysicalObject ;
                  rdfs:range  xsd:dateTime .
bim:plannedEnd    rdf:type    owl:DatatypeProperty ;
                  rdfs:domain bim:PhysicalObject ;
                  rdfs:range  xsd:dateTime .
```

**제안: HierarchyNode에 AWP semantics 추가**

```turtle
# HierarchyNode subclasses for AWP
bim:AreaNode        rdfs:subClassOf  bim:HierarchyNode .
bim:UnitNode        rdfs:subClassOf  bim:HierarchyNode .
bim:DisciplineNode  rdfs:subClassOf  bim:HierarchyNode .

# AWP Work Package
bim:WorkPackage     rdfs:subClassOf  bim:Container .
bim:CWP             rdfs:subClassOf  bim:WorkPackage .  # Construction Work Package
bim:EWP             rdfs:subClassOf  bim:WorkPackage .  # Engineering Work Package
```

### 3.2 DXTnavis 구현 계획

`DynamicScheduleBuilder.cs`의 `ExtractTaskGroupsFromMemory` 수정:

```
현재: slot column 값 없으면 -> continue (객체 스킵)
변경: slot column 값 없으면 -> 계층 ancestor에서 Area/Unit/Discipline 추출하여 fallback 값 사용
```

이렇게 하면 **별도의 외부 매핑 테이블 없이** 모든 객체가 AWP 구조에 포함됩니다.

### 3.3 온톨로지 프로젝트와의 연동 흐름

```
DXTnavis (Navisworks Plugin)
  +-- AllProperties CSV (12,009 objects, spatial + classification)
  +-- geometry.csv (BBox, centroid coordinates)
  +-- Dynamic Schedule CSV (temporal: start/end/duration/sequence)  <- NEW
  |
  v
first-ontology-project
  +-- Phase 2b: refined_class -> OWL rdf:type  (spatial + classification) DONE
  +-- Phase 3: Neo4j KG (261K edges)                                     DONE
  +-- Phase ??: Temporal integration (schedule -> ScheduleTask triples)   NEW
       +-- 183-299 task groups (audit-verified, depth 4-5; see §6)
       +-- NearestNeighbor spatial ordering -> construction sequence
       +-- AWP WorkPackage generation from hierarchy (path-pattern based)
```

---

## 4. Recommendations

### For ontology project

1. **R1: Schema extension** -- `ScheduleTask` 클래스 또는 temporal data properties 추가 검토
2. **R2: HierarchyNode typing** -- Level 2/3/4 노드에 `AreaNode`/`UnitNode`/`DisciplineNode` 타입 부여 검토
3. **R3: Schedule CSV ingest** -- DXTnavis가 생성하는 Dynamic Schedule CSV를 Phase 2 파이프라인에 추가하여 temporal triples 생성
4. **R4: 4D SPARQL queries** -- "Area A2에서 2026-06에 시공되는 객체는?" 같은 시공간 질의 가능

### For DXTnavis

5. **R5: Hierarchy fallback 구현** -- `DynamicScheduleBuilder.cs`에서 slot 값 없는 객체에 ancestor 이름 사용 (구현 예정)
6. **R6: Schedule CSV export** -- 온톨로지 프로젝트가 ingest할 수 있는 형식으로 export

---

## 5. Cross-references

| 자료 | 위치 |
|------|------|
| DXTnavis PR #5 (NearestNeighbor) | [tygwan/DXTnavis#5](https://github.com/tygwan/DXTnavis/pull/5) |
| OWL schema (28 classes) | `src/bimkg/ontology/schema.py` |
| M1: Piping misclassification | `docs/findings/2026-04-12-M1-piping-misclassification/` |
| AllProperties CSV (12,009 objects) | DXTnavis Full Export |
| Dynamic Schedule Builder | `DXTnavis/Services/DynamicScheduleBuilder.cs` |

---

## 6. Audit & Evidence (R3 compliance)

본 finding 의 모든 수치는 다음 재현 가능한 audit 로 검증되었습니다:

```bash
.venv/bin/python docs/findings/2026-04-22-M7-hierarchy-awp-scheduling/audit.py
.venv/bin/python docs/findings/2026-04-22-M7-hierarchy-awp-scheduling/make_figures.py
```

### 6.1 Audit script 산출물 (CSV evidence)

| 파일 | 내용 | rows |
|------|------|---:|
| [`data/coverage_by_source.csv`](data/coverage_by_source.csv) | Total / SP3D Geom / Pipeline / PipeRun / Nav-only 카운트 | 6 |
| [`data/non_pipeline_class_breakdown.csv`](data/non_pipeline_class_breakdown.csv) | 4,964 비배관 SP3D 의 refined_class 분포 + README estimate 비교 | 5 |
| [`data/hierarchy_level_distribution.csv`](data/hierarchy_level_distribution.csv) | level_val 별 객체 수 + AWP role 가설 라벨 | 10 |
| [`data/level2_node_inventory.csv`](data/level2_node_inventory.csv) | system_path segs[1] 의 distinct 값 (Level 2 = Area 가설 검증) | 5 |
| [`data/sp3d_property_coverage.csv`](data/sp3d_property_coverage.csv) | 5개 핵심 SP3D property non-null 비율 | 5 |
| [`data/task_count_simulation.csv`](data/task_count_simulation.csv) | Pipeline-only vs Hierarchy depth 2-7 task 수 | 7 |

### 6.2 Figures

| 파일 | 내용 |
|------|------|
| [`figures/01_object_source_coverage.png`](figures/01_object_source_coverage.png) | 12,009 객체의 출처 분포 donut chart (Pipeline 24% / SP3D-no-Pipe 41% / Nav-only 34%) |
| [`figures/02_estimate_vs_actual.png`](figures/02_estimate_vs_actual.png) | README 추정 vs audit 실측 5개 항목 비교 (49-132% 오차) |
| [`figures/03_hierarchy_depth_dist.png`](figures/03_hierarchy_depth_dist.png) | level_val 분포 — 객체 대부분이 depth 6-8 에 집중 (AWP 가설의 depth 2-4 와 불일치) |
| [`figures/04_task_count_simulation.png`](figures/04_task_count_simulation.png) | prefix depth 별 task 수 (log scale) + Pipeline-only baseline + README ~677 라인 |

### 6.3 Audit verdict 요약

**EXACT MATCH (6/7 coverage 수치)**:
- Total 12,009 / SP3D Geom 7,890 / Pipeline 2,926 / PipeRun 2,926 / SP3D-no-Pipe 4,964 / Nav-only 4,119

**WRONG (정정 필요)**:
- Eqp Type 0: ~300 → **153** (-49%)
- 비배관 4,964 분류: Structure +115% / Electrical +98% / Equipment +132% / Other -72%
- "Level 2 = Area" 가설: TRAINING 노드 단일이 98.8% 점유 → segs[1] 매칭 불가
- "~677 task" projection: 어떤 prefix depth (2-7) 에서도 재현 안 됨

**구조적 결론 유지**:
- Coverage gap (24% → 100%) 는 정량적으로 실재 (9,083 객체 누락)
- Hierarchy fallback 전략 자체는 유효 (단, AWP slot 추출 로직은 path-pattern 기반이어야)
- Schedule CSV ingest → temporal triples 제안 (§3) 영향 없음

### 6.4 후속 작업 (Phase 4+ 로드맵 후보)

이 audit 가 만든 두 갈래:

1. **Algorithm impact analysis** — DXTnavis 의 NearestNeighbor 정렬, time-mapping strategy (Hybrid/FixedDuration/ObjectCountBased) 별 schedule diff 정량화
2. **Path-pattern AWP extractor** — system_path 의 "A\d+", "Refining Area", "Sulphur Recovery Area" 같은 의미 패턴을 추출하여 **진짜 Area/Unit/Discipline 노드** identify (single-Level fallback 보다 정확)
