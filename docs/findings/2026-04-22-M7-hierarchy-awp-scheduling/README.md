# 2026-04-22 — M7 — Hierarchy-based AWP Scheduling: 12,009 objects with temporal dimension

**Severity**: 🟡 ENHANCEMENT (ontology gap — no temporal coverage)
**Status**: 🔄 Implementation in progress (DXTnavis PR #5 + schedule builder)
**Discovered by**: DXTnavis Dynamic Schedule v2.0 all-object scheduling analysis
**Affects**: Container/HierarchyNode modeling, temporal scheduling, AWP work packaging

---

## 1. Finding

### 1.1 Hierarchy encodes AWP structure

Navisworks 모델 계층(Level 0–9)이 **자연스러운 AWP(Advanced Work Packaging) 구조**를 인코딩하고 있습니다.
현재 온톨로지의 `HierarchyNode`는 순수 containment로만 모델링되어 있지만,
실제 데이터에서 **Level 2 = Area, Level 3 = Unit, Level 4 = Discipline** 패턴이 일관적으로 나타납니다.

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

**4,964개의 비배관 SP3D 객체**가 스케줄에서 누락됩니다:
- `StructuralMember` (MemberPartPrismatic 등): ~1,200개
- `ElectricalComponent` (CableTray, Cableway): ~400개
- `Equipment` (ProcessEquipment, Civil): ~300개
- 기타 (HVAC, Insulation 등): ~3,000개

### 1.3 Hierarchy fallback으로 전체 커버리지 달성

계층 ancestor 이름을 fallback slot 값으로 사용하면 **12,009개 전체 객체**를 AWP 구조로 그룹핑할 수 있습니다.

**시뮬레이션 결과** (현재 378 task → 예상 677 task):

| 지표 | Pipeline-only (현재) | Hierarchy fallback (예상) |
|------|---------------------|--------------------------|
| Task 수 | 378 | ~677 |
| 커버 객체 | 2,926 (24%) | 12,009 (100%) |
| 그룹핑 기준 | Pipeline/PipeRun | Area/Unit/Discipline |
| 누락 discipline | 구조, 전기, 장비, 토목 | 없음 |

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
| `SP3D\|Eqp Type 0` | ~300 / 12,009 | ~2.5% (장비만) |
| `Item\|Type` | 7,890 / 12,009 | 65.7% (= SP3D\|Name과 동일 범위) |

### 2.3 비배관 객체 분류 (4,964개)

| 온톨로지 클래스 | 대표 display_name | 추정 수 |
|----------------|-------------------|---------|
| `StructuralMember` | MemberPartPrismatic, MemberSystem | ~1,200 |
| `ElectricalComponent` | CableTray, Cableway, Cable Tray Part | ~400 |
| `Equipment` -> 하위 | ProcessEquipment, CivilElements | ~300 |
| `UncategorizedObject` | HgrProfile, Cover, Insulation | ~3,000 |

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
       +-- 677 task groups with PlannedStart/PlannedEnd
       +-- NearestNeighbor spatial ordering -> construction sequence
       +-- AWP WorkPackage generation from hierarchy
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
