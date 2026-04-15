# Ontology Registration Cheatsheet

**목적**: Foundry Ontology Manager UI 에 Copy-Paste 용 입력값 모음.
**전제**: AI FDE 의 "Ontology Registration Guide" 문서가 Foundry 에 있고, 이 치트시트는 그 가이드를 보조.

---

## Phase 1 — Interfaces (3개)

### ✅ HasPressureTemp (완료)

2 properties, Piping-only mixin.

### 🔄 HasSP3DMetadata (다음)

**Interface 메타**

| 필드 | 입력값 |
|---|---|
| Display Name | `Has SP3D Metadata` |
| API Name | `HasSP3DMetadata` |
| Description | `Mixin interface for BIM objects that carry SmartPlant 3D (SP3D) design metadata. Implemented by all 6 BIM object types (BimPiping, BimStructural, BimEquipment, BimElectrical, BimHvac, BimOther).` |
| Searchable | ❌ 체크 해제 |
| Branch | `master` |

**Properties (3)**

| # | API Name | Type | Display Name | Description |
|---|---|---|---|---|
| 1 | `sp3dMoniker` | String | `SP3D Moniker` | SP3D internal moniker reference |
| 2 | `sp3dName` | String | `SP3D Name` | SP3D object name |
| 3 | `sp3dStatus` | String | `SP3D Status` | SP3D design status |

---

### 🔄 BimObject (메인, 34 properties)

**Interface 메타**

| 필드 | 입력값 |
|---|---|
| Display Name | `BIM Object` |
| API Name | `BimObject` |
| Description | `Base interface for all BIM (Building Information Modeling) objects extracted from a refining plant SP3D model via Navisworks. Implemented by 6 object types: BimPiping, BimStructural, BimEquipment, BimElectrical, BimHvac, BimOther.` |
| Searchable | ❌ 체크 해제 |
| Branch | `master` |

**Properties (34)** — 5 그룹으로 분류하여 입력 편의성 확보

#### Group A — Identity & Display (4 props)

| # | API Name | Type | Display Name | Description |
|---|---|---|---|---|
| 1 | `objectId` | String | `Object ID` | Primary key, unique across all types |
| 2 | `displayName` | String | `Display Name` | Human-readable name |
| 3 | `title` | String | `Title` | Title property for search/display |
| 4 | `systemPath` | String | `System Path` | Full Navisworks tree path |

#### Group B — Classification (4 props)

| # | API Name | Type | Display Name | Description |
|---|---|---|---|---|
| 5 | `refinedClass` | String | `Refined Class` | Classification: Piping/Structure/Equipment/Electrical/HVAC/Other |
| 6 | `originalClass` | String | `Original Class` | Pre-refinement class from Navisworks |
| 7 | `classificationConfidence` | String | `Classification Confidence` | HIGH or LIKELY_BUG |
| 8 | `classificationConfidenceReason` | String | `Classification Confidence Reason` | Rationale for confidence label |

#### Group C — Relationships (FK columns, 2 props)

| # | API Name | Type | Display Name | Description |
|---|---|---|---|---|
| 9 | `parentId` | String | `Parent ID` | FK for parent-child hierarchy |
| 10 | `groupId` | String | `Group ID` | Connected component group ID |

#### Group D — Spatial Geometry (10 props)

| # | API Name | Type | Display Name | Description |
|---|---|---|---|---|
| 11 | `centroidX` | Double | `Centroid X` | X coordinate of centroid (meters) |
| 12 | `centroidY` | Double | `Centroid Y` | Y coordinate of centroid (meters) |
| 13 | `centroidZ` | Double | `Centroid Z` | Z coordinate of centroid (elevation, meters) |
| 14 | `bboxMinX` | Double | `BBox Min X` | Bounding box minimum X |
| 15 | `bboxMinY` | Double | `BBox Min Y` | Bounding box minimum Y |
| 16 | `bboxMinZ` | Double | `BBox Min Z` | Bounding box minimum Z |
| 17 | `bboxMaxX` | Double | `BBox Max X` | Bounding box maximum X |
| 18 | `bboxMaxY` | Double | `BBox Max Y` | Bounding box maximum Y |
| 19 | `bboxMaxZ` | Double | `BBox Max Z` | Bounding box maximum Z |
| 20 | `bboxVolumeM3` | Double | `BBox Volume (m³)` | Bounding box volume in cubic meters |

#### Group E — Mesh / 3D Media (5 props)

⚠️ **`meshUri` 는 나중에 Object Type 등록 시 "Media Reference" 타입으로 설정** (Interface 에서는 String 으로 선언).

| # | API Name | Type | Display Name | Description |
|---|---|---|---|---|
| 21 | `meshUri` | String | `Mesh URI` | Path to GLB mesh in bim_mesh Media Set (mesh/{objectId}.glb) |
| 22 | `meshQuality` | String | `Mesh Quality` | full_mesh / fbx_supplemented / skipped_container / box_placeholder |
| 23 | `hasRealMesh` | Boolean | `Has Real Mesh` | True if an actual mesh file exists |
| 24 | `vertexCount` | Long | `Vertex Count` | Number of vertices in the mesh |
| 25 | `triangleCount` | Long | `Triangle Count` | Number of triangles in the mesh |

#### Group F — Physical & Graph Properties (2 props)

| # | API Name | Type | Display Name | Description |
|---|---|---|---|---|
| 26 | `adjacencyCount` | Long | `Adjacency Count` | Number of spatially adjacent objects |
| 27 | `dryWeightKg` | Double | `Dry Weight (kg)` | Dry weight in kilograms |

#### Group G — Flags (7 props, all Boolean)

| # | API Name | Type | Display Name | Description |
|---|---|---|---|---|
| 28 | `isContainer` | Boolean | `Is Container` | Navisworks grouping node flag |
| 29 | `isParentBox` | Boolean | `Is Parent Box` | Parent box contamination flag (M3 finding) |
| 30 | `isBboxPlaceholder` | Boolean | `Is BBox Placeholder` | Bounding box placeholder flag |
| 31 | `isHidden` | Boolean | `Is Hidden` | Hidden object flag |
| 32 | `graphParticipant` | Boolean | `Graph Participant` | Participates in adjacency graph |
| 33 | `hasOwnGeometry` | Boolean | `Has Own Geometry` | Has its own geometry (not inherited) |
| 34 | `verdict` | String | `Verdict` | OK_MESH / OK_FBX / SKIP_CONTAINER / SKIP_NO_GEOMETRY / OK_LINE_MESH / SKIP_IS_HIDDEN |

**Total**: 34 properties
- Group A (4) + B (4) + C (2) + D (10) + E (5) + F (2) + G (7) = 34 ✓

---

## 💡 입력 팁

### 34개 property 를 빠르게 입력하는 법

Foundry Ontology Manager 의 Interface 편집 UI 는 통상 3가지 입력 방식 지원:

**방식 1: 하나씩 "Add Property" 버튼 클릭**
- 제일 안전하지만 34번 클릭 + 입력 필요
- 오타 시 찾기 쉬움

**방식 2: Bulk paste (제공된다면)**
- "Add from CSV" 또는 "Bulk add" 버튼 존재 시 활용
- 위 표에서 컬럼 복사하여 붙여넣기

**방식 3: JSON/YAML import (고급 사용자)**
- UI 하단 "Code view" / "Raw edit" 모드에서 JSON 붙여넣기
- API Name + Type + Description 만 넣으면 나머지는 자동

### 입력 중 저장 권장

매 10개 property 입력 후 "Save as Draft" 또는 유사 버튼으로 중간 저장.
실수로 페이지 새로고침 시 잃는 것 방지.

### Type 이름 Foundry 표기 확인

Foundry UI 에서 Type 이름이 다르게 표시될 수 있음:
- `Double` = Double / Float64
- `String` = String / Text
- `Long` = Long / Int64
- `Boolean` = Boolean / Bool
- `Date` / `Timestamp` — 구분 주의

---

## Phase 2 — Object Types (8개)

상세 치트시트는 Phase 1 완료 후 추가 작성 예정.

대략 순서:
1. BimPiping (가장 풍부, baseline)
2. BimStructural (delta from Piping)
3. BimEquipment
4. BimElectrical
5. BimHvac
6. BimOther
7. BimPipeline (신규 aggregate)
8. BimPipeRun (신규 aggregate)

---

## Phase 3 — Link Types (4개)

1. adjacentTo — BimObject ↔ BimObject (Many-to-Many, symmetric flag on edge)
2. hasParent — BimObject → BimObject (Many-to-One)
3. belongsToPipeline — BimPiping → BimPipeline (Many-to-One)
4. pipeRunInPipeline — BimPipeRun → BimPipeline (Many-to-One)

(belongsToPipeRun 은 Pipeline Builder 작업 후 별도 등록 — D-AIFDE-14)

---

## 🎯 현재 위치

- [x] Phase 1.1 HasPressureTemp ✓
- [ ] Phase 1.2 HasSP3DMetadata
- [ ] Phase 1.3 BimObject
- [ ] ⚠️ Review Changes 에서 6개 legacy Object Types 제거
- [ ] Phase 2 Object Types (8개)
- [ ] Phase 3 Link Types (4개)
