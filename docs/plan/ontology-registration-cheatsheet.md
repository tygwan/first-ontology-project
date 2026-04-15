# Ontology Registration Cheatsheet

**목적**: Foundry Ontology Manager UI 에 Copy-Paste 용 입력값 모음.
**전제**: AI FDE 의 "Ontology Registration Guide" 문서를 Foundry 에서 참조하면서 이 치트시트로 실제 입력.

---

## 📦 기준 RID (참조용)

### Interface RIDs (Phase 1 완료)
```
BimObject:        ri.ontology.main.interface.62a67f81-2af0-4c88-a421-579f3df6587b
HasSP3DMetadata:  ri.ontology.main.interface.2a9d1741-f6df-4e57-92ba-199a6d3ebb1d
HasPressureTemp:  ri.ontology.main.interface.9f79fc16-8fca-47af-af09-4a5db806d4d2
```

### Dataset RIDs (backing datasets)
```
bim_piping:              ri.foundry.main.dataset.2388ddc2-3c83-4ef3-a7df-fef11024bb4e
bim_structural:          ri.foundry.main.dataset.32658e86-ad1b-4adb-8acf-c3c409a21661
bim_equipment:           ri.foundry.main.dataset.5e250030-37c1-4475-aaac-8a9e9bf42e64
bim_electrical:          ri.foundry.main.dataset.29338c90-e5be-4db7-86f9-eb0449340873
bim_hvac:                ri.foundry.main.dataset.914af224-32c8-48c5-b419-47eab341e33b
bim_other:               ri.foundry.main.dataset.87c921ea-cfcb-4ba5-b656-4bcacde11804
bim_pipelines:           ri.foundry.main.dataset.722b3a55-9562-4d01-a95b-df859c62fea7
bim_piperuns:            ri.foundry.main.dataset.4c65a69a-75f3-4ece-ba52-c266d597f3a2
bim_adjacent_to:         ri.foundry.main.dataset.d6f789d4-54d7-49d1-9351-b20e825624dc
bim_has_parent:          ri.foundry.main.dataset.159d949e-fe9b-4267-a20e-57512e0600d8
bim_belongs_to_pipeline: ri.foundry.main.dataset.97db7363-a24e-4cd8-870c-39450ba9bbfa
bim_in_group:            ri.foundry.main.dataset.0e57446a-bbc6-4443-bec8-7cbf58103e65
```

---

## Phase 1 — Interfaces ✅ 완료

- ✅ HasPressureTemp (2 props)
- ✅ HasSP3DMetadata (3 props)
- ✅ BimObject (34 props)

---

## Phase 2 — Object Types (8개)

### 🔑 중요 개념

Object Type 등록 절차 (모든 8개 공통):
1. **Create Object Type** → name, API name, display name, description
2. **Select Backing Dataset** → 위 RID 참조
3. **Set Primary Key** → object_id (또는 BimPipeline 의 pipeline_name, BimPipeRun 의 piperun_id)
4. **Set Title Property** → 통상 display_name
5. **Implement Interfaces** → BimObject + HasSP3DMetadata + (HasPressureTemp는 BimPiping 만)
6. **Map Properties** → dataset column → interface property / class-specific property
7. **Configure Property Types** → Media Reference (meshUri 만), 나머지 자동
8. **Save as Draft** → Review Changes → Apply

### ⚠️ meshUri → Media Reference 설정 (모든 6개 타입 공통)

기본값은 String 으로 import 되지만, **3D viewer 기능 활성화를 위해 Media Reference 로 변경** 필요:
- Property `meshUri` 편집
- **Type 을 "Media Reference" 로 변경**
- **Media Set** 선택: `bim_mesh` (위 경로 또는 RID 로 참조)
- **Path Template**: 빈 값 그대로 (dataset 의 mesh_uri 컬럼 값이 이미 `mesh/{object_id}.glb` 포맷)

### ⚠️ Implement Interfaces 3가지 방식

| Type | BimObject | HasSP3DMetadata | HasPressureTemp |
|---|:-:|:-:|:-:|
| BimPiping | ✓ | ✓ | ✓ |
| BimStructural | ✓ | ✓ | ✗ |
| BimEquipment | ✓ | ✓ | ✗ |
| BimElectrical | ✓ | ✓ | ✗ |
| BimHvac | ✓ | ✓ | ✗ |
| BimOther | ✓ | ✓ | ✗ |
| BimPipeline | (partial) | ✗ | ✗ |
| BimPipeRun | (partial) | ✗ | ✗ |

BimPipeline, BimPipeRun 은 공통 interface 구조 다름 — 별도 스펙 (아래).

---

### 2.1 BimPiping (3,062 objects — 가장 풍부한 타입, baseline)

**메타데이터**

| 필드 | 값 |
|---|---|
| Display Name | `BIM Piping` |
| API Name | `BimPiping` |
| Object Type ID | `bim-piping` |
| Description | `Refinery piping components: flanges, valves, pipes, fittings. 3,062 objects from SP3D via Navisworks.` |
| Backing Dataset | `bim_piping` (RID 위 참조) |
| Primary Key | `object_id` |
| Title Property | `display_name` (또는 `title`) |
| Implements | BimObject + HasSP3DMetadata + HasPressureTemp |

**Interface Property 매핑** (Interface 의 34 + 3 + 2 = 39 매핑)

| Interface Property | Dataset Column | Type |
|---|---|---|
| objectId | object_id | String |
| displayName | display_name | String |
| title | title | String |
| refinedClass | refined_class | String |
| originalClass | original_class | String |
| classificationConfidence | classification_confidence | String |
| classificationConfidenceReason | classification_confidence_reason | String |
| systemPath | system_path | String |
| parentId | parent_id | String |
| groupId | group_id | String |
| centroidX | centroid_x | Double |
| centroidY | centroid_y | Double |
| centroidZ | centroid_z | Double |
| bboxMinX | bbox_min_x | Double |
| bboxMinY | bbox_min_y | Double |
| bboxMinZ | bbox_min_z | Double |
| bboxMaxX | bbox_max_x | Double |
| bboxMaxY | bbox_max_y | Double |
| bboxMaxZ | bbox_max_z | Double |
| bboxVolumeM3 | bbox_volume_m3 | Double |
| meshUri | mesh_uri | **Media Reference** (bim_mesh) |
| meshQuality | mesh_quality | String |
| hasRealMesh | has_real_mesh | Boolean |
| vertexCount | vertex_count | Long |
| triangleCount | triangle_count | Long |
| adjacencyCount | adjacency_count | Long |
| dryWeightKg | dry_weight_kg | Double |
| isContainer | is_container | Boolean |
| isParentBox | is_parent_box | Boolean |
| isBboxPlaceholder | is_bbox_placeholder | Boolean |
| isHidden | is_hidden | Boolean |
| graphParticipant | graph_participant | Boolean |
| hasOwnGeometry | has_own_geometry | Boolean |
| verdict | verdict | String |
| sp3dMoniker | sp3d_sp3d_moniker | String |
| sp3dName | sp3d_name | String |
| sp3dStatus | sp3d_status | String |
| designPressureKpa | design_pressure_kpa | Double |
| designTemperatureC | design_temperature_c | Double |

**Piping-specific Properties (18 추가)** — Interface 외 class-specific

| API Name | Dataset Column | Type | Description |
|---|---|---|---|
| sp3dPipeline | sp3d_pipeline | String | Pipeline name (FK to BimPipeline) |
| sp3dPipeRun | sp3d_pipe_run | String | Pipe run subdivision (FK to BimPipeRun) |
| sp3dNpd | sp3d_npd | String | Nominal pipe diameter (raw) |
| sp3dFlowDirection | sp3d_flow_direction | String | |
| sp3dDescription | sp3d_description | String | BOM/part description |
| sp3dCommodityCode | sp3d_commodity_code | String | |
| sp3dConstructionType | sp3d_construction_type | String | |
| sp3dLocation | sp3d_location | String | |
| sp3dShortCode | sp3d_short_code | String | |
| sp3dReportingType | sp3d_reporting_type | String | |
| npdEnd1M | npd_end1_m | Double | Parsed NPD end 1 (meters) |
| npdEnd2M | npd_end2_m | Double | Parsed NPD end 2 (meters) |
| lengthM | length_m | Double | Pipe length (meters) |
| sp3dInsulationPurpose | sp3d_insulation_purpose | String | |
| sp3dInsulationThickness | sp3d_insulation_thickness | String | |
| refiningRule | refining_rule | String | Lineage |
| refiningRuleVersion | refining_rule_version | String | Lineage |
| navItemGuid | nav_item_guid | String | Navisworks GUID (M1 forensic trail, D-AIFDE-9) |

**Nav 메타 (Tier 4, 6 추가)**

| API Name | Dataset Column | Type |
|---|---|---|
| navItemSourceFileName | nav_item_source_file_name | String |
| navItemType | nav_item_type | String |
| navClassDisplayName | nav_class_display_name | String |
| levelVal | level_val | Long |
| isLeaf | is_leaf | Boolean |
| childCount | child_count | Long |

**Total BimPiping**: 34 (Interface) + 3 (SP3D) + 2 (PressureTemp) + 18 (Piping-specific) + 6 (Nav) = 63 ✓ (matches Registration Guide spec)

---

### 2.2 BimStructural (4,840 objects — delta from BimPiping)

**메타데이터**

| 필드 | 값 |
|---|---|
| Display Name | `BIM Structural` |
| API Name | `BimStructural` |
| Object Type ID | `bim-structural` |
| Description | `Refinery structural members: beams, columns, foundations, gratings, steel members.` |
| Backing Dataset | `bim_structural` |
| Primary Key | `object_id` |
| Title Property | `display_name` |
| Implements | BimObject + HasSP3DMetadata (⚠️ HasPressureTemp 제외) |

**Interface Property 매핑**: BimPiping 과 동일하게 34 + 3 = 37 매핑 (HasPressureTemp 2개 skip)

**Class-specific Properties (14 추가 — Piping 대비 다름)**

| API Name | Dataset Column | Type | Description |
|---|---|---|---|
| sp3dMaterial | sp3d_material | String | Non-empty in structural (빈값 Piping 과 다름) |
| sp3dMaterialName | sp3d_material_name | String | |
| sp3dMaterialType | sp3d_material_type | String | |
| sp3dSectionName | sp3d_section_name | String | e.g., W14x30 |
| widthM | width_m | Double | |
| depthM | depth_m | Double | |
| sp3dFireproofingLabel | sp3d_fireproofing_label | String | |
| sp3dFireRating | sp3d_fire_rating | String | |
| sp3dDescription | sp3d_description | String | |
| sp3dLocation | sp3d_location | String | |
| sp3dReportingType | sp3d_reporting_type | String | |
| refiningRule | refining_rule | String | |
| refiningRuleVersion | refining_rule_version | String | |
| navItemGuid | nav_item_guid | String | |

+ **Nav 메타 6** (동일)

**Skip from Piping baseline** (piping-specific, structural 에 없음):
sp3dPipeline, sp3dPipeRun, sp3dNpd, sp3dFlowDirection, sp3dCommodityCode,
sp3dConstructionType, sp3dShortCode, npdEnd1M, npdEnd2M, lengthM,
designPressureKpa, designTemperatureC (HasPressureTemp 에서 skip)

**Total BimStructural**: 34 + 3 + 14 + 6 = 59 ✓

---

### 2.3 BimEquipment (770 objects)

**메타데이터**

| 필드 | 값 |
|---|---|
| Display Name | `BIM Equipment` |
| API Name | `BimEquipment` |
| Object Type ID | `bim-equipment` |
| Description | `Refinery process equipment: vessels, pumps, heat exchangers, compressors.` |
| Backing Dataset | `bim_equipment` |
| Primary Key | `object_id` |
| Title Property | `display_name` |
| Implements | BimObject + HasSP3DMetadata (⚠️ HasPressureTemp 제외 — 데이터 0% fill) |

**Class-specific Properties (10 추가)**

| API Name | Dataset Column | Type | Description |
|---|---|---|---|
| sp3dEquipmentName | sp3d_equipment_name | String | **KEY** — Equipment tag (V-1001 등) |
| sp3dType | sp3d_type | String | Vessel / Pump / Exchanger 등 |
| sp3dEqpType0 | sp3d_eqp_type_0 | String | Classification level 0 |
| sp3dEqpType1 | sp3d_eqp_type_1 | String | Level 1 |
| sp3dEqpType2 | sp3d_eqp_type_2 | String | Level 2 |
| sp3dLocation | sp3d_location | String | |
| sp3dArea | sp3d_area | String | Plant area designation |
| refiningRule | refining_rule | String | |
| refiningRuleVersion | refining_rule_version | String | |
| navItemGuid | nav_item_guid | String | |

+ **Nav 메타 6**

**Total BimEquipment**: 34 + 3 + 10 + 6 = 53 (55 에서 HasPressureTemp 2개 제외)

---

### 2.4 BimElectrical (1,053 objects)

**메타데이터**

| 필드 | 값 |
|---|---|
| Display Name | `BIM Electrical` |
| API Name | `BimElectrical` |
| Object Type ID | `bim-electrical` |
| Description | `Refinery electrical components: cable trays, conduits, junction boxes.` |
| Backing Dataset | `bim_electrical` |
| Primary Key | `object_id` |
| Implements | BimObject + HasSP3DMetadata |

**Class-specific Properties (8 추가)**

| API Name | Dataset Column | Type |
|---|---|---|
| sp3dDescription | sp3d_description | String |
| sp3dCommodityCode | sp3d_commodity_code | String |
| lengthM | length_m | Double |
| sp3dLocation | sp3d_location | String |
| sp3dShortCode | sp3d_short_code | String |
| refiningRule | refining_rule | String |
| refiningRuleVersion | refining_rule_version | String |
| navItemGuid | nav_item_guid | String |

+ **Nav 메타 6**

**Total BimElectrical**: 34 + 3 + 8 + 6 = 51

---

### 2.5 BimHvac (125 objects)

**메타데이터**

| 필드 | 값 |
|---|---|
| Display Name | `BIM HVAC` |
| API Name | `BimHvac` |
| Object Type ID | `bim-hvac` |
| Description | `Refinery HVAC components: ducts, ventilation systems. Smallest dataset (125 objects).` |
| Backing Dataset | `bim_hvac` |
| Primary Key | `object_id` |
| Implements | BimObject + HasSP3DMetadata |

**Class-specific Properties (7 추가)**

| API Name | Dataset Column | Type |
|---|---|---|
| sp3dType | sp3d_type | String |
| sp3dDescription | sp3d_description | String |
| lengthM | length_m | Double |
| sp3dLocation | sp3d_location | String |
| refiningRule | refining_rule | String |
| refiningRuleVersion | refining_rule_version | String |
| navItemGuid | nav_item_guid | String |

+ **Nav 메타 6**

**Total BimHvac**: 34 + 3 + 7 + 6 = 50

---

### 2.6 BimOther (2,159 objects)

**메타데이터**

| 필드 | 값 |
|---|---|
| Display Name | `BIM Other` |
| API Name | `BimOther` |
| Object Type ID | `bim-other` |
| Description | `Catch-all for unclassified BIM objects. Contains containers, placeholders, line meshes. Highest non-physical ratio.` |
| Backing Dataset | `bim_other` |
| Primary Key | `object_id` |
| Implements | BimObject + HasSP3DMetadata |

**Class-specific Properties**: 0 (모든 유용한 속성이 Interface 커버)

+ **Nav 메타 6** + lineage 2 (refining_rule*)

**Total BimOther**: 34 + 3 + 6 + 2 = 45

**주의**: bim_other 에는 `OK_LINE_MESH` (8) 와 `SKIP_IS_HIDDEN` (7) verdict 가 있는 유일한 타입. Workshop 필터에서 이 그룹 특별 처리 가능.

---

### 2.7 BimPipeline (147 objects, 신규 aggregate)

**메타데이터**

| 필드 | 값 |
|---|---|
| Display Name | `BIM Pipeline` |
| API Name | `BimPipeline` |
| Object Type ID | `bim-pipeline` |
| Description | `Refinery piping system (pipeline). Aggregates components per sp3d_pipeline. 147 distinct pipelines.` |
| Backing Dataset | `bim_pipelines` (신규 aggregate) |
| Primary Key | `pipeline_name` |
| Title Property | `pipeline_name` |
| Implements | (BimObject 적용 안 됨 — aggregate 타입이라 objectId 없음) |

**Properties (29개)** — 전부 class-specific

| API Name | Dataset Column | Type |
|---|---|---|
| pipelineName | pipeline_name | String (PK) |
| componentCount | component_count | Long |
| pipeRunCount | pipe_run_count | Long |
| totalDryWeightKg | total_dry_weight_kg | Double |
| meanPressureKpa | mean_pressure_kpa | Double |
| maxPressureKpa | max_pressure_kpa | Double |
| minPressureKpa | min_pressure_kpa | Double |
| meanTemperatureC | mean_temperature_c | Double |
| maxTemperatureC | max_temperature_c | Double |
| bboxVolumeTotalM3 | bbox_volume_total_m3 | Double |
| centroidX | centroid_x | Double |
| centroidY | centroid_y | Double |
| centroidZ | centroid_z | Double |
| bboxMinX | bbox_min_x | Double |
| bboxMinY | bbox_min_y | Double |
| bboxMinZ | bbox_min_z | Double |
| bboxMaxX | bbox_max_x | Double |
| bboxMaxY | bbox_max_y | Double |
| bboxMaxZ | bbox_max_z | Double |
| meshCoveragePct | mesh_coverage_pct | Double |
| valveCount | valve_count | Long |
| flangeCount | flange_count | Long |
| elbowCount | elbow_count | Long |
| teeCount | tee_count | Long |
| reducerCount | reducer_count | Long |
| fbxSupplementedCount | fbx_supplemented_count | Long |
| likelyBugCount | likely_bug_count | Long |
| representativeSystemPath | representative_system_path | String |
| ingestedAtUtc | ingested_at_utc | **Timestamp** (or Date, D-AIFDE-14) |

---

### 2.8 BimPipeRun (378 objects, 신규 aggregate)

**메타데이터**

| 필드 | 값 |
|---|---|
| Display Name | `BIM Pipe Run` |
| API Name | `BimPipeRun` |
| Object Type ID | `bim-pipe-run` |
| Description | `Piping construction subdivision (pipe run). FK to BimPipeline. 378 entities across 147 pipelines (avg 2.6/pipeline).` |
| Backing Dataset | `bim_piperuns` |
| Primary Key | `piperun_id` (composite: `pipeline_name::pipe_run_name`) |
| Title Property | `pipe_run_name` |

**Properties (26)** — 전부 class-specific

| API Name | Dataset Column | Type |
|---|---|---|
| piperunId | piperun_id | String (PK) |
| pipelineName | pipeline_name | String (FK to BimPipeline) |
| pipeRunName | pipe_run_name | String |
| componentCount | component_count | Long |
| totalDryWeightKg | total_dry_weight_kg | Double |
| meanPressureKpa | mean_pressure_kpa | Double |
| maxPressureKpa | max_pressure_kpa | Double |
| meanTemperatureC | mean_temperature_c | Double |
| maxTemperatureC | max_temperature_c | Double |
| centroidX | centroid_x | Double |
| centroidY | centroid_y | Double |
| centroidZ | centroid_z | Double |
| bboxMinX | bbox_min_x | Double |
| bboxMinY | bbox_min_y | Double |
| bboxMinZ | bbox_min_z | Double |
| bboxMaxX | bbox_max_x | Double |
| bboxMaxY | bbox_max_y | Double |
| bboxMaxZ | bbox_max_z | Double |
| bboxVolumeTotalM3 | bbox_volume_total_m3 | Double |
| meshCoveragePct | mesh_coverage_pct | Double |
| valveCount | valve_count | Long |
| flangeCount | flange_count | Long |
| elbowCount | elbow_count | Long |
| teeCount | tee_count | Long |
| fbxSupplementedCount | fbx_supplemented_count | Long |
| ingestedAtUtc | ingested_at_utc | **Timestamp** |

---

## 🎯 Phase 2 진행 순서 (권장)

```
1. BimPiping  (가장 복잡, 63 props, baseline) — 약 30분
    ↓ AI FDE audit
2. BimStructural (delta)                      — 약 15분
    ↓
3. BimEquipment (delta)                       — 약 10분
    ↓
4. BimElectrical (delta)                      — 약 10분
    ↓
5. BimHvac (delta)                            — 약 10분
    ↓
6. BimOther (delta)                           — 약 10분
    ↓ AI FDE audit (6 BIM types 전체)
7. BimPipeline (aggregate, 29 props)          — 약 10분
    ↓
8. BimPipeRun (aggregate, 26 props)           — 약 10분
    ↓ AI FDE audit (2 aggregate types)
Phase 2 완료 → Phase 3 Link Types
```

**예상 총 소요**: 1.5–2 시간

---

## Phase 3 — Link Types (4개)

### 3.1 adjacentTo (BimObject ↔ BimObject)

| 필드 | 값 |
|---|---|
| Link Type ID | `adjacent-to` |
| Backing Dataset | `bim_adjacent_to` (110,173 edges) |
| Cardinality | Many-to-Many |
| Source | BimObject (any type) via `source_object_id` → `object_id` |
| Target | BimObject (any type) via `target_object_id` → `object_id` |
| Symmetric | Yes (flag on `is_symmetric`) |

Link Properties:

| API Name | Column | Type |
|---|---|---|
| relationType | relation_type | String (overlap / touch / neartouch) |
| distanceM | distance_m | Double |
| overlapVolumeM3 | overlap_volume_m3 | Double |
| toleranceM | tolerance_m | Double |
| isSymmetric | is_symmetric | Boolean |

⚠️ **Cross-type 처리**: source/target 둘 다 BimPiping/BimStructural/BimEquipment/BimElectrical/BimHvac/BimOther 중 어느 것이든 가능. UI 에서 6×6=36 조합 지정 필요할 수 있음. 또는 Interface `BimObject` 기반 단일 정의 가능 (권장).

---

### 3.2 hasParent (BimObject → BimObject)

| 필드 | 값 |
|---|---|
| Link Type ID | `has-parent` |
| Backing Dataset | `bim_has_parent` (12,008 edges) |
| Cardinality | Many-to-One |
| Source | BimObject (child) via `child_object_id` → `object_id` |
| Target | BimObject (parent) via `parent_object_id` → `object_id` |

Link Properties:

| API Name | Column | Type |
|---|---|---|
| childLevel | child_level | Double |

---

### 3.3 belongsToPipeline (BimPiping → BimPipeline)

| 필드 | 값 |
|---|---|
| Link Type ID | `belongs-to-pipeline` |
| Backing Dataset | `bim_belongs_to_pipeline` (2,926 edges) |
| Cardinality | Many-to-One |
| Source | BimPiping via `object_id` → `object_id` |
| Target | BimPipeline via `pipeline_name` → `pipeline_name` |

Link Properties:

| API Name | Column | Type |
|---|---|---|
| pipeRunName | pipe_run_name | String |

---

### 3.4 pipeRunInPipeline (BimPipeRun → BimPipeline)

| 필드 | 값 |
|---|---|
| Link Type ID | `pipe-run-in-pipeline` |
| Backing Dataset | `bim_piperuns` (378 rows, self-referencing) |
| Cardinality | Many-to-One |
| Source | BimPipeRun via `piperun_id` |
| Target | BimPipeline via `pipeline_name` → `pipeline_name` |

---

### (Deferred) belongsToPipeRun

D-AIFDE-14 에 따라 Pipeline Builder 로 `bim_belongs_to_pipeline` → `bim_belongs_to_piperun` 파생 dataset 생성 후 등록. Phase 2 등록 직후 cleanup task.

---

## 🎯 현재 위치

- [x] Phase 1 — 3 Interfaces 등록 ✓
- [ ] Phase 2 — Object Types 8개
  - [ ] 2.1 BimPiping
  - [ ] 2.2 BimStructural
  - [ ] 2.3 BimEquipment
  - [ ] 2.4 BimElectrical
  - [ ] 2.5 BimHvac
  - [ ] 2.6 BimOther
  - [ ] 2.7 BimPipeline
  - [ ] 2.8 BimPipeRun
- [ ] Phase 3 — Link Types (4개)
- [ ] Post-registration cleanup
  - [ ] Pipeline Builder: bim_belongs_to_piperun 파생
  - [ ] belongsToPipeRun Link Type 등록
  - [ ] KPI 조인 (Phase 3 operational layer 와 함께)
