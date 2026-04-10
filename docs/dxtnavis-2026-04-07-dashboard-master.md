# DXTnavis 2026-04-07 Dashboard — Master Document

> **목적**: 이 문서는 `scripts/analysis/260407/dashboard.html` 가 무엇으로부터 만들어졌고, 무엇을 보여주며, 어떤 인사이트가 이미 검증되었는지를 한 곳에 정리한 권위 문서입니다. 이 문서만 가지고도 dashboard 를 처음부터 재현할 수 있도록 데이터 출처 · 컬럼 · 빌드 단계 · 가정 · 검증 결과를 모두 기록합니다.
>
> **재현 가능성 기준**: 새 개발자가 이 문서 + repo 만 가지고 1시간 이내에 동일한 dashboard 를 복원할 수 있어야 합니다.

**문서 작성일**: 2026-04-10
**대상 데이터셋**: `data/raw/dxtnavis/2026-04-07/` (DXTnavis v1.4.0 export, 12,009 BIM 객체)
**관련 메모**: `docs/analysis/dxtnavis-2026-04-07-baseline-insights.md`, `docs/analysis/dxtnavis-2026-04-07-powerbi-integration.md`

---

## 1. 한 줄 요약

> dashboard 에 보이는 모든 숫자는 **DXTnavis v1.4.0 가 2026-04-07 18:46:50 에 한 번 찍어낸 export** 한 덩어리에서 파생됩니다. 백엔드 처리 1단계 + Python 빌더 1단계 = 총 2번의 derivation 만 거치고, 모든 mesh 수치는 GLB 8,656 파일 직접 파싱으로 0 diff 검증되었습니다.

---

## 2. 데이터 흐름 (3 layers + 1 export)

```
┌─────────────────────────────────────────────────────────────────────┐
│ ① PRODUCER RAW (DXTnavis v1.4.0)                                    │
│    유일한 ground truth — 다른 모든 것은 여기에서 파생됨              │
├─────────────────────────────────────────────────────────────────────┤
│  data/raw/dxtnavis/2026-04-07/                                      │
│    manifest.json                  (metadata + 12009 object snapshots)│
│    AllProperties_*.csv            (12009 × 136 cols, raw properties)│
│    geometry.csv                   (12009 × 18 cols, bbox + mesh count)│
│    validation.csv                 (12009 × 33 cols, verdict + flags)│
│    adjacency.csv                  (110173 producer spatial edges)   │
│    connected_groups.csv           (3355 connected components)       │
│    tessellation_failures.csv      (671 failures, mostly empty)      │
│    spatial_relationships.ttl      (RDF triples — NOT used)          │
│  external mesh dir (outside repo, separate location):               │
│    mesh/<oid>.glb × 8656          (binary glTF, ground-truth mesh)  │
└────────────────────┬────────────────────────────────────────────────┘
                     │ semantic-backend (C# .NET 8) ingests
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ② BACKEND DERIVED                                                   │
│    canonical SQLite + CSV projections                               │
├─────────────────────────────────────────────────────────────────────┤
│  data/working/dxtnavis/                                             │
│    dxtnavis-semantic.db           (258 MB SQLite store)             │
│    refining/dxtref-*/                                               │
│      refining_all_objects.csv     (12009 × 16 canonical fields)     │
│      class_distribution.csv       (5 classes)                       │
│    schedule/dxtsch-*/             (multiple runs by groupBy)        │
│      schedule_all_classes.csv     + task_object_links.csv           │
│    neo4j/dxtneo-*/                (Neo4j projection — NOT used)     │
└────────────────────┬────────────────────────────────────────────────┘
                     │ scripts/analysis/260407/build_dashboard_data.py
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ③ DASHBOARD AGGREGATE                                               │
│    one JSON payload + one HTML viewer                               │
├─────────────────────────────────────────────────────────────────────┤
│  scripts/analysis/260407/                                           │
│    build_dashboard_data.py        (Python builder, stdlib only)     │
│    dashboard_data.json            (12.3 MB pretty)                  │
│    dashboard_data.min.json        (8.3 MB compact, fetched by HTML) │
│    dashboard.html                 (63 KB, Plotly + Tabulator UI)    │
│    build_standalone.py            (bundles HTML + JSON in 1 file)   │
│    dashboard_standalone.html      (8.4 MB self-contained snapshot)  │
└────────────────────┬────────────────────────────────────────────────┘
                     │ build_timeliner_csv.py reads ③
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ④ TIMELINER EXPORT (Navisworks 4D simulation)                       │
├─────────────────────────────────────────────────────────────────────┤
│  data/working/dxtnavis/timeliner/                                   │
│    synth_timeliner.csv            (6721 task rows × 13 cols)        │
│    synth_task_objects.csv         (12009 task↔object links)         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer ① 원천 (Producer raw)

### 3.1 export 위치

이 export 는 원래 단일 폴더 안에 있었지만 **GLB mesh 가 너무 커서 repo 에 안 들어감** — 두 위치로 나뉘어 있습니다.

| 항목 | 위치 |
|---|---|
| CSV + manifest | `data/raw/dxtnavis/2026-04-07/` (repo 안) |
| GLB mesh | `C:/Users/Yoon taegwan/Desktop/AWP_2025/개발폴더/테스트폴더/260407 온톨로지테스트/dxtnavis_export_20260407_184650/mesh/` (repo 밖) |

manifest.json 의 `meshUri` 필드가 `mesh/<oid>.glb` 로 GLB 를 참조합니다. 두 위치를 합치면 원래 export 폴더가 복원됩니다.

### 3.2 파일 인벤토리

| 파일 | 크기 | 행 | 열 | 인코딩 | 용도 |
|---|--:|--:|--:|---|---|
| `manifest.json` | 7.0 MB | 12,009 obj | — | UTF-8 BOM | producer 의 self-snapshot · ground truth |
| `AllProperties_20260407_184650.csv` | 13.1 MB | 12,009 | 136 | UTF-8 BOM | 모든 raw 속성 (한·영 혼합 컬럼명) |
| `geometry.csv` | 3.4 MB | 12,009 | 18 | UTF-8 BOM | bbox / 부피 / 중심점 / mesh count |
| `validation.csv` | 2.7 MB | 12,009 | 33 | UTF-8 BOM | verdict / mesh quality / adjacency count |
| `adjacency.csv` | 18.9 MB | 110,173 | 10 | UTF-8 BOM | producer 공간 인접 관계 |
| `connected_groups.csv` | 791 KB | 3,355 | 15 | UTF-8 BOM | connected components |
| `tessellation_failures.csv` | 96 KB | 671 | 5 | UTF-8 BOM | mesh tessellation 실패 (대부분 컨테이너) |
| `spatial_relationships.ttl` | 48.6 MB | — | — | UTF-8 | RDF triples — **NOT used by dashboard** (adjacency.csv 가 동일 정보) |
| `spatial_summary.txt` | 505 B | — | — | UTF-8 | 사람 읽기용 요약 |
| `mesh/*.glb` | — | 8,656 files | — | binary glTF | producer ground-truth mesh |

### 3.3 manifest.json 스키마

```jsonc
{
  "metadata": {
    "version": "1.0.0",
    "generator": "DXTnavis v1.4.0",
    "exportDate": "2026-04-07T09:48:50Z",
    "projectName": "DXTnavis Export",
    "objectCount": 12009,
    "globalBoundingBox": { "min": {x,y,z}, "max": {x,y,z} },
    "meshCount": 8656
  },
  "objects": [
    {
      "objectId": "8dd55e0a-2aee-5612-8465-b8f7ff0e7da3",  // GUID lowercase
      "displayName": "For Review.nwd",
      "category": "파일",
      "bbox":     { "min": {x,y,z}, "max": {x,y,z} },
      "centroid": { "x": 34.65, "y": 79.01, "z": 7.08 },
      "hasMesh": false,
      "meshUri": null,  // "mesh/<oid>.glb" 또는 null
      "meshQuality": "skipped_container",
      "vertexCount": 0,
      "triangleCount": 0
    },
    // ... 12009 objects total
  ]
}
```

### 3.4 geometry.csv 컬럼

| 컬럼 | 타입 | 의미 |
|---|---|---|
| `ObjectId` | GUID | join key (전 파일 공통) |
| `DisplayName` | string | Navisworks display name |
| `Category` | string | raw 카테고리 (한국어 가능, e.g. "파일") |
| `MinX/MinY/MinZ/MaxX/MaxY/MaxZ` | float (m) | axis-aligned bounding box |
| `CentroidX/Y/Z` | float (m) | bbox 중심점 |
| `Volume` | float (m³) | bbox 부피 (실제 mesh 부피 아님) |
| `HasMesh` | bool | "True" 또는 "False" |
| `MeshUri` | string | `mesh/<oid>.glb` 또는 빈값 |
| `MeshQuality` | enum | full_mesh / fbx_supplemented / line_mesh / box_placeholder / skipped_container |
| `VertexCount` | int | **GLB 직접 파싱 값과 0 diff 검증 완료** |
| `TriangleCount` | int | **GLB 직접 파싱 값과 0 diff 검증 완료** |

### 3.5 validation.csv 컬럼 (주요)

| 컬럼 | 의미 |
|---|---|
| `ObjectId` | join key |
| `Verdict` | OK_MESH / OK_FBX / OK_LINE_MESH / **SKIP_CONTAINER** / SKIP_NO_GEOMETRY |
| `MeshQuality` | geometry.csv 와 동일 |
| `TessResult` | tessellation 결과 코드 |
| `ContainerStatus` | 컨테이너 분류 상태 |
| `HasGeometry` | bool |
| `HasRealMesh` | bool |
| `GlbExists` | bool |
| `IsLeaf` | bool — Navisworks 트리에서 leaf 여부 |
| `ChildCount` | int — 자식 객체 수 |
| `AdjacencyCount` | int — 이 객체가 참여하는 adjacency edge 수 |
| `GroupId` | string — connected component id |
| `BBoxVolume` | float — bbox 부피 중복 (geometry 와 동일) |

### 3.6 adjacency.csv 스키마

| 컬럼 | 의미 |
|---|---|
| `SourceObjectId` | edge 시작점 GUID |
| `TargetObjectId` | edge 끝점 GUID |
| `Distance` | float (m) — 두 mesh 표면 최단 거리 |
| `OverlapVolume` | float (m³) — overlap 인 경우 교차 부피 |
| `RelationType` | **overlap** (79.5%) / **near-touch** (14.4%) / **touch** (6.1%) |
| `SourceCategory` / `TargetCategory` | 양쪽의 raw 카테고리 |
| `Tolerance` | float — near-touch 판정 임계값 |

총 110,173 edges, 8,656 unique objects 가 참여 (즉 mesh 없는 객체는 edge 없음).

### 3.7 connected_groups.csv

| 컬럼 | 의미 |
|---|---|
| `GroupId` | G001~ 식별자 |
| `ElementCount` | 그룹 내 객체 수 |
| `EdgeCount` | 그룹 내 edge 수 |
| `TotalVolume` | bbox 부피 합 |
| `DominantCategory` | 다수 카테고리 |
| `BBoxMin/Max{X,Y,Z}` | 그룹 전체 bbox |
| `Centroid{X,Y,Z}` | 가중 중심점 |
| `MemberObjectIds` | **세미콜론 구분 GUID 리스트** — 거대 그룹은 한 셀이 319 KB 까지 |

3,355 그룹 중 **giant component 1 개 (8,626 객체, 71.8 %)** + **3,353 singleton (컨테이너 = 27.9 %)** + 작은 그룹 1.

### 3.8 AllProperties_*.csv (136 컬럼)

ObjectId / ParentId / Level / 객체이름 + **SmartPlant 3D|\*** 81개 + **재질|\*** 14개 + **항목|\*** 14개 + **형상|\*** 8개. 모든 값에 type prefix (`DisplayString:`, `Double:`, `Int32:`, ...) 가 붙어 있어 strip 필요.

**Dashboard 가 사용하는 16개 컬럼**:

| 원본 컬럼 | dashboard JSON key | tier | 채움률 |
|---|---|---|--:|
| `SmartPlant 3D\|Status` | `status` | 1 | 61.5% |
| `SmartPlant 3D\|Reporting Type` | `rtype` | 1 | 57.5% |
| `SmartPlant 3D\|Material` | `mat` | 1 | 20.0% |
| `SmartPlant 3D\|Spec Name` | `spec` | 1 | 5.1% |
| `SmartPlant 3D\|User Last Modified` | `mby` (enum index) | 1 | 61.1% |
| `SmartPlant 3D\|NPD` | `npd` | 2 | 24.4% |
| `항목\|유형` | `itype` (Top-200 truncation) | 2 | 100% |
| `항목\|이름` | `iname` (search only) | 2 | 100% |
| `SmartPlant 3D\|Dry Weight` | `dwt` | 3 | 44.7% |
| `SmartPlant 3D\|Length` | `len` | 3 | 14.5% |
| `SmartPlant 3D\|Cut Length` | `clen` | 3 | 13.0% |
| `SmartPlant 3D\|Width` | `wid` | 3 | 14.8% |
| `SmartPlant 3D\|Depth` | `dep` | 3 | 13.0% |
| `SmartPlant 3D\|Design Max Pressure` | `pmax` | 3 | 24.4% |
| `SmartPlant 3D\|Design Max Temperature` | `tmax` | 3 | 24.4% |
| `SmartPlant 3D\|Date Created` | `dcre` (ISO 8601) | 4 | 61.5% |
| `SmartPlant 3D\|Date Last Modified` | `dmod` (ISO 8601) | 4 | 61.5% |

**의도적 미로딩** (refining 이 권위 있음, 이중 로드 금지):
`SmartPlant 3D|Pipeline`, `PipeRun`, `Equipment Name`, `Location`, `Level`, `Name`, `System Path`.

**드롭됨** (오해 소지 또는 가치 없음):
`SmartPlant 3D|Construction Type` (refining 의 ConstructionType 과 동일), `항목|이름` (refining DisplayName 과 845 행만 차이), `형상|삼각형` (mesh triangle 이 아니라 Navisworks 내부 scene graph 카운터), `재질|광택/반사/...` 13개 RGB float, `Iso Sheet No`/`Spool` 거의 빈값.

**31개 컬럼이 1% 미만 채움률** — `Manufacturer`, `Wet Weight`, `WetCG{X,Y,Z}`, `DryCG{X,Y,Z}` 등.

### 3.9 GLB 파일 (mesh 직접 검증)

**위치**: 외부 폴더 (위 §3.1).
**형식**: binary glTF 2.0 (12 byte header + JSON chunk + BIN chunk).

**Verification**: `scripts/analysis/260407/` 에 임시 파서로 8,656 개 모두 직접 파싱:

| 검증 | 결과 |
|---|---|
| GLB 파일 수 | **8,656 == manifest.meshCount == validation 의 mesh-bearing rows** |
| GLB total vertices | **11,725,350 == manifest sum == geometry.csv sum** (0 diff) |
| GLB total triangles | **3,913,142 == manifest sum == geometry.csv sum** (0 diff) |
| 객체별 vertex/triangle | **0 / 8,656 diff** (어느 객체도 차이 없음) |

→ DXTnavis v1.4.0 의 GLB → CSV 직렬화는 증명 가능하게 lossless. 사용자가 OBJ 대시보드에서 겪었던 silent loss 패턴은 GLB 에서는 구조적으로 발생하지 않음.

---

## 4. Layer ② 백엔드 파생 (semantic-backend)

### 4.1 백엔드 정체

C# .NET 8 ASP.NET Core minimal API. 위치: `semantic-backend/src/SemanticBackendMock/`. 핵심 서비스: `Services/DxtnavisSemanticStore.cs`.

**시작 방법**:
```bash
cd semantic-backend/src/SemanticBackendMock
dotnet run --no-launch-profile --urls "http://127.0.0.1:5050"
```

### 4.2 SQLite 정규 store

`data/working/dxtnavis/dxtnavis-semantic.db` (258 MB) 가 모든 백엔드 작업의 정규 저장소. 한 번 import 된 후에는 schedule generation 등 후속 호출이 이 db 에서 직접 읽음 (raw 파일을 다시 안 읽음).

### 4.3 백엔드 엔드포인트 (dashboard 가 의존)

| 엔드포인트 | 용도 |
|---|---|
| `POST /dxtnavis/bundle/import` | 한 export 디렉터리를 한 번에 refining + schedule + neo4j 까지 처리 (≈10s for 12009 objects) |
| `POST /dxtnavis/refining/import` | refining 만 단독 |
| `POST /dxtnavis/schedule/generate` | refining 이미 import 된 상태에서 schedule 만 재생성 |
| `GET /dxtnavis/schedule/latest` | 최근 schedule run 메타 |

**Bundle import 호출 예** (Korean path 회피용 relative path):
```bash
curl -X POST http://127.0.0.1:5050/dxtnavis/bundle/import \
  -H "Content-Type: application/json" \
  -d '{"exportDirectoryPath":"2026-04-07"}'
```

**Schedule generate 호출 예**:
```bash
curl -X POST http://127.0.0.1:5050/dxtnavis/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{"groupBy":"Pipeline","sortBy":"DisplayName","sortOrder":"asc","exportCsv":true}'
```

**Supported `groupBy` 값**: `Class`, `ConstructionType`, `Pipeline`, `PipeRun`, `SystemPath`, `Status`, `Material`, `EquipmentName`, `Location`, `Level`, `DisplayName`, `ObjectId`, `ParentId`, `SourceFileName`, 또는 raw CSV 의 임의 컬럼명.

### 4.4 refining canonical store

위치: `data/working/dxtnavis/refining/dxtref-<timestamp>-<hash>/refining_all_objects.csv`
크기: 69.5 MB (단일 파일에 RawPropertiesJson 포함이라 큼)
스키마: 12,009 × 16 cols

| 컬럼 | 의미 |
|---|---|
| `ImportId` | refining run id |
| `ObjectId` | GUID |
| `ParentId` | 부모 GUID |
| `Class` | **백엔드가 heuristic 으로 derive** — Piping/Structure/Equipment/Support/Other |
| `DisplayName` | 정규화된 이름 |
| `Level` | "0".."9" 문자열 |
| `SystemPath` | 슬래시 구분 hierarchical path |
| `Pipeline` | 파이프라인 ID (Piping 만) |
| `PipeRun` | 파이프 런 (Piping 만) |
| `Location` | 좌표 문자열 (희소) |
| `Status` | "For Review.vue" 등 워크플로 상태 |
| `ConstructionType` | "New" / "Future" / 빈값 |
| `EquipmentName` | 장비 식별자 (Equipment 만) |
| `SourceFileName` | **백엔드 파싱 버그로 0.008% 만 채움** — memory plan #6 |
| `SourceFilePath` | 99.99 % 채움 (실질적 source file 식별자) |
| `RawPropertiesJson` | 원본 SmartPlant 속성 전체 JSON dump |

**Class 분포**: Other 5,917 (49%) / Piping 2,926 (24%) / Structure 1,791 (15%) / Support 715 (6%) / Equipment 660 (5%).

### 4.5 schedule runs (현재 4 종류 보존)

`data/working/dxtnavis/schedule/dxtsch-*/`:

| groupBy | task 수 | 가장 큰 그룹 | unassigned 비율 |
|---|--:|---|--:|
| Class | 5 | Other 5,917 | 49 % |
| ConstructionType | 3 | `<unassigned>` 8,521 | 71 % |
| **Pipeline** | 158 | `<unassigned>` 9,083 | 76 % |
| SystemPath | 3,369 | `<unassigned>` 4,253 | 35 % |

각 run 디렉터리 안:
- `schedule_all_classes.csv` — 1 row per task: `RunId, TaskId, TaskName, GroupBy, GroupKey, SortBy, SortValue, SortOrder, TaskOrder, ObjectCount`
- `task_object_links.csv` — 1 row per (task, object): `RunId, TaskId, ObjectId, ObjectOrder, DisplayName, Class, Level`

### 4.6 사용 안 하는 파생물

- `data/working/dxtnavis/neo4j/dxtneo-*/` — Neo4j 프로젝션 CSV 들 (12,009 obj nodes / 459,757 prop nodes / 5 class nodes / 3,874 ctx nodes / 5 task nodes / 787,679 edges). **Dashboard 가 직접 안 읽음** — Neo4j 에 별도로 import 해야 의미 있음.

---

## 5. Layer ③ Dashboard aggregate

### 5.1 빌더: `build_dashboard_data.py`

**의존**: stdlib only (csv, json, math, glob, re, datetime, collections)
**입력**: 위 §3 + §4 의 파일들
**출력**: `dashboard_data.json` (pretty 12.3 MB) + `dashboard_data.min.json` (compact 8.3 MB)
**실행**: `python scripts/analysis/260407/build_dashboard_data.py` (≈3초)

### 5.2 빌드 단계 (순서대로)

1. **refining_all_objects.csv 로드** — 12,009 객체 base record (id, name, cls, lvl, sys, pipeline, piperun, location, construction, equipment)
2. **geometry.csv merge** — bbox / vol / diag / cx / cy / cz / vc / tc / VolumeBucket / SizeBucket
3. **validation.csv merge** — meshq / verdict / adjcount / gid / hasmesh / hasrealmesh
4. **AllProperties enrichment** (Tier 1~4) — `csv.reader` + 명시적 인덱싱 (DictReader 회피로 `Constuction Type` 오타 silent loss 방지)
   - String fields → strip `DisplayString:` 접두사
   - Number fields → `parse_number_with_unit` (단위 정규화 안 함, mm/m/kg/t/psi/bar 혼재 허용)
   - Date fields → `parse_korean_datetime` (오전/오후 → AM/PM 수동 파싱, ISO 8601 출력)
   - User Last Modified → enum index (11 distinct → 정수 `mby`)
   - Dedup 가드: ctype vs construction (드롭), iname vs name (keep, 845 diff)
5. **connected_groups.csv 로드** — giant component 식별, member set 매핑
6. **adjacency.csv 로드** — degree counter, class-pair aggregate
7. **task_object_links.csv 로드** — Class 기반 schedule (백엔드 baseline)
8. **mesh_richness 버킷 계산** — none / <100 / 100-1k / 1k-10k / >=10k
9. **synth schedule 계산** — composite key + duration estimation (자세히는 §6)
10. **backend_schedules 스캔** — `data/working/dxtnavis/schedule/dxtsch-*/` 에서 4 grouping 의 latest run 메타 수집
11. **itype Top-200 truncation** — 빈도 낮은 3,311 itype 값 객체 row 에서 제거 (~160 KB 절감)
12. **None/empty prune** — 객체 row 에서 빈 필드 제거 (size 절감)
13. **JSON write** — pretty + min 두 버전

### 5.3 객체 row 의 모든 키 (38개 가능)

빈 값은 prune 되므로 객체마다 다름:

```
id, name, cls, lvl, sys, pipeline, piperun, location, construction, equipment,
cat, vol, diag, cx, cy, cz, vc, tc,
meshq, verdict, adjcount, gid, hasmesh, hasrealmesh,
status, rtype, mat, spec, mby,
npd, itype, iname,
dwt, len, clen, wid, dep, pmax, tmax,
dcre, dmod,
deg, in_giant,
sk, tk
```

### 5.4 agg 키 (24개)

| 키 | 내용 |
|---|---|
| `headline` | 25+ 헤드라인 숫자 (총 객체, 거대 그룹, 컨테이너, 메시, 합성 task, duration 등) |
| `classes` | `[{cls, n}, ...]` 5개 |
| `meshq` | mesh quality 분포 |
| `level_class` | level × class heatmap matrix |
| `pair_class` | 클래스 쌍별 producer edge 수 (overlap/touch/neartouch 분리) |
| `pipeline_top` | top 20 pipeline by object count |
| `hubs` | top 25 producer adjacency hub 객체 |
| `giant_group` | 거대 그룹 구성 (by class, by meshq) |
| `group_sizes_top` | top 20 connected components |
| `extent` | global X/Y/Z 범위 |
| `status` | Working/Approved/LightPart 카운트 |
| `mat` | Material 4종 |
| `rtype` | Reporting Type |
| `spec` | top 12 Spec Name |
| `users` | enum lookup (11 names) |
| `npd_top` | top 15 NPD |
| `itype_top` | top 15 항목\|유형 |
| `dwt_sum_by_cls` | 클래스별 dry weight 합 |
| `dcre_months` | 월별 created/modified 카운트 |
| `dcre_extent` | min/max month + coverage |
| `mesh_richness` | 5 buckets |
| **`synth_tasks`** | 6,721 task 메타 (id/level/class/package/n/duration/start_date/end_date/dwt_total/tri_total) |
| `synth_tasks_by_cls` | 클래스별 synth task 카운트 |
| **`backend_schedules`** | 4 backend grouping run 메타 |

---

## 6. Synth schedule 계산 상세 (가장 중요한 derivation)

### 6.1 Composite key

```
schedule_key = (level_num, class_seq, package, -priority, oid)
```

| 차원 | 출처 | 의미 |
|---|---|---|
| `level_num` | refining `Level` (정수) | bottom-up by floor (1 → 9) |
| `class_seq` | hardcoded map | **시공 순서**: Structure 1 → Support 2 → Equipment 3 → Piping 4 → Other 5 (빈도순 CLASS_ORDER 와 다름) |
| `package` | `_package_for(r)` (아래) | 작업 묶음 |
| `priority` | `_priority_for(r)` (아래) | 같은 묶음 안의 우선순위 (heaviest first) |
| `oid` | ObjectId | tiebreaker — 결정적 정렬 |

### 6.2 `_package_for(r)` 의 fallback chain

```python
def _package_for(r):
    cls = r.get("cls", "")
    if cls == "Piping":
        return r.get("pipeline") or r.get("piperun") or "(no-pipeline)"
    if cls == "Equipment":
        return r.get("equipment") or "(no-equipment)"
    sp = r.get("sys") or ""
    if sp:
        # SystemPath 의 첫 2 segments
        parts = sp.split("/", 2)
        return "/".join(parts[:2]) if parts else sp
    # 1차 fallback: itype 가 의미 있을 때
    itype = r.get("itype")
    if itype and itype not in {"Geometry Group", "Geometry"}:
        return f"type:{itype}"  # e.g., "type:Insulation Volume"
    # 2차 fallback: 15m × 15m XY zone
    cx, cy = r.get("cx"), r.get("cy")
    if cx is not None and cy is not None:
        return f"Zone[{int(cx//15):>+03d},{int(cy//15):>+03d}]"
    # 최후
    return r.get("construction") or "(no-package)"
```

**검증 결과**: Piping 객체 2,926 개 모두에 대해 `synth.package == 백엔드 Pipeline GroupKey` 100% 일치. → synth 의 Piping 분리는 백엔드 Pipeline grouping 과 증명적으로 동등하고, 비파이핑에 대한 fallback (itype + zone) 이 추가된 superset.

### 6.3 `_priority_for(r)`

```python
def _priority_for(r):
    for k in ("dwt", "deg", "tc"):
        v = r.get(k)
        if v is not None and v > 0:
            return v
    return 0
```

같은 패키지 안에서 무거운 것 → 인접도 큰 것 → mesh 풍부한 것 순. 음수 부호로 정렬하여 큰 값이 앞에 오게.

### 6.4 Task 분할 결과

| 항목 | 값 |
|---|--:|
| 총 synth tasks | **6,721** |
| 분포 | L0:1 / L1:1 / L2:3 / L3:1 / L4:7 / L5:26 / L6:370 / L7:1,084 / L8:1,616 / L9:49 (sum 3,158 before refinement, 6,721 after) |
| 가장 큰 task (객체 수) | 137 obj — T6721 L9 Other `type:Insulation Volume` |
| 비교 (refinement 전) | 2,037 obj — T0362 L6 Other `(no-package)` |
| 분할 개선 비율 | **14× reduction in max task size** |

### 6.5 Duration estimation (가정)

**Class 별 man-hour rate** (process plant 산업 통계 기반, 의도적으로 coarse):

```python
MH_PER_KG = {
    "Structure": 0.025,   # ~40 kg/mh for steel erection
    "Piping":    0.040,   # ~25 kg/mh for medium-bore + welds
    "Equipment": 0.020,   # ~50 kg/mh for heavy setting
    "Support":   0.030,
    "Other":     0.010,   # default light assembly
}
HOURS_PER_DAY = 8.0
OBJ_BASE_DAYS = 0.05    # task with no dwt → 0.05 day per object
MIN_TASK_DAYS = 0.25    # every task at least 2 hours
CREW_PARALLELISM = 12   # 12 crews work in parallel — compresses calendar
BASE_DATE = datetime(2026, 1, 1)
```

**Per-task formula**:
```
duration_days = max(MIN_TASK_DAYS,
                    (dwt_total × MH_PER_KG[class]) / 8     if dwt_total > 0
                    n_objects × OBJ_BASE_DAYS              otherwise)
```

**Calendar mapping** (cumulative work / parallelism):
```
cal_start = cumulative_mh_days / CREW_PARALLELISM
cal_end = cal_start + duration_days / CREW_PARALLELISM
```

**결과**:
| 지표 | 값 |
|---|---|
| 순차 실행 시 총 work | 8,426 mh-days (≈23 년) |
| 12 병렬 crew 압축 후 | **702.2 days (1.9 년)** |
| 프로젝트 window | **2026-01-01 → 2027-12-04** |

### 6.6 모든 가정 (이 dashboard 에서 derive 된 것들)

| 가정 | 값 | 위치 | 영향 |
|---|---|---|---|
| Class 시공 순서 | Structure 1 / Support 2 / Equipment 3 / Piping 4 / Other 5 | `CLASS_SEQ` in builder | task ordering |
| Construction zone 크기 | 15 m × 15 m | `ZONE_X`, `ZONE_Y` | spatial fallback granularity |
| Generic itype | "Geometry Group", "Geometry" 는 무시 | `_GENERIC_ITYPES` | itype fallback 트리거 |
| MH per kg | class 별 0.010~0.040 | `MH_PER_KG` | duration |
| 일일 작업 시간 | 8 h | `HOURS_PER_DAY` | duration |
| 최소 task duration | 0.25 day (2 h) | `MIN_TASK_DAYS` | task floor |
| 객체 기본 duration | 0.05 day/obj (no dwt) | `OBJ_BASE_DAYS` | duration fallback |
| 병렬 crew 수 | 12 | `CREW_PARALLELISM` | calendar 압축 |
| 프로젝트 시작일 | 2026-01-01 | `BASE_DATE` | calendar offset |
| itype Top-200 truncation | 빈도 200위 밖 값 객체 row 에서 제거 | post-process | JSON 크기 |
| User Last Modified enum | 11 distinct → 정수 인덱스 | `agg.users` lookup | JSON 크기 (~100 KB 절감) |

이 가정들 중 어느 하나라도 실제 프로젝트와 다르면 빌더의 해당 상수만 바꾸고 재실행하면 됩니다.

---

## 7. Layer ④ Timeliner export

### 7.1 빌더: `build_timeliner_csv.py`

**입력**: `dashboard_data.min.json`
**출력**: `data/working/dxtnavis/timeliner/synth_timeliner.csv` + `synth_task_objects.csv`
**실행**: `python scripts/analysis/260407/build_timeliner_csv.py` (≈1초)

### 7.2 synth_timeliner.csv 컬럼

| 컬럼 | 의미 |
|---|---|
| `TaskId` | T0001 ~ T6721 |
| `TaskName` | `{TaskId} L{level} {class}: {package[:40]}` |
| `TaskType` | "Construct" (literal) |
| `StartDate` | YYYY-MM-DD |
| `EndDate` | YYYY-MM-DD |
| `DurationDays` | float |
| `Level` | 0..9 |
| `Class` | Piping/Structure/... |
| `Package` | full package string |
| `ObjectCount` | int |
| `DryWeightTons` | float (3 decimals) |
| `TriangleCount` | int |
| `SelectionSetName` | TaskId (for attach-by-name) |

### 7.3 Navisworks Timeliner import 절차

1. Timeliner → Data Sources → Add → **Microsoft Excel/CSV**
2. Source 파일: `synth_timeliner.csv`
3. Field selector 매핑:
   - `Task Type` ← `TaskType`
   - `Planned Start` ← `StartDate`
   - `Planned End` ← `EndDate`
   - `User 1` ← `Level`
   - `User 2` ← `Class`
   - `User 3` ← `Package`
4. Refresh → 6,721 task tree 생성
5. SelectionSet attach: `synth_task_objects.csv` 의 ObjectId 리스트로 각 task 에 selection 연결

---

## 8. Dashboard UI 인벤토리

### 8.1 헤더 + 도움말 패널

- 헤더: 제목 + "12,009 objects · interactive view" + status
- **6 섹션 도움말 패널** (`<details open>` 으로 기본 펼침):
  1. 이게 뭔가요?
  2. 3 단계로 사용하세요 (슬라이서 → KPI/차트 → 테이블)
  3. 어떤 정보를 볼 수 있나요 (8 카테고리)
  4. 이미 데이터에 보이는 인사이트 7 가지
  5. 인사이트 도출 방법 — 슬라이서 조합 5 가지
  6. 숫자 읽을 때 주의 5 가지

### 8.2 KPI 카드 (총 15개, 3 행 × 5)

| # | 라벨 | 의미 | 클래스 |
|--:|---|---|---|
| 1 | Filtered objects | 슬라이서 통과 객체 수 | highlight |
| 2 | In giant group | 거대 그룹 비율 | ok |
| 3 | Containers | 컨테이너 비율 | warn |
| 4 | Full mesh | 전체 mesh 비율 | — |
| 5 | Piping rows | 파이핑 비율 | — |
| 6 | Avg producer deg | 평균 인접도 | — |
| 7 | Dry weight | 합계 (t) | highlight |
| 8 | Length total | 합계 (m) | — |
| 9 | Scrap length | len − cut_length 합 | warn |
| 10 | With material | 자재 보유 객체 수 | — |
| 11 | Avg design P | 평균 설계 압력 | — |
| 12 | Modified ≤12mo | 최근 1년 수정 객체 | ok |
| 13 | Total triangles | 11.7 M | highlight |
| 14 | Total vertices | 3.91 M | — |
| 15 | Avg tri / meshed | 452 | — |
| 16 | Synth tasks | 활성 task / 6,721 | highlight |
| 17 | Project window | 2026-01-01 → 2027-12-04 | — |
| 18 | Duration | 702.2 d (12 crews) | ok |

### 8.3 슬라이서 (총 16개, 좌측 패널)

| 슬라이서 | 형태 | 데이터 소스 |
|---|---|---|
| Search | text input | name + pipeline + cat + id + spec + npd + iname |
| Class | checkbox | `agg.classes` |
| Mesh Quality | checkbox | `agg.meshq` |
| Level | checkbox | level distinct |
| Volume Bucket | checkbox | computed |
| Mesh Richness | checkbox | `agg.mesh_richness` |
| Status | checkbox | `agg.status` |
| Material | checkbox | `agg.mat` |
| Reporting Type | checkbox | `agg.rtype` |
| Spec Name | checkbox | `agg.spec` |
| User Last Modified | checkbox | computed from `agg.users` |
| NPD | checkbox | `agg.npd_top` |
| In Giant Group | radio (all/yes/no) | `o.in_giant` |
| Min Degree | range slider 0..500 | `o.deg` |
| Z range | dual range | `o.cz` |
| Date Last Modified | from/to date inputs + include-undated checkbox | `o.dmod` |
| Schedule rank | range slider 1..12009 | `o.sk` |
| **Scatter color by** | radio (class/rank/tri) | `state.filters.scatterColorBy` |

### 8.4 차트 (총 18개)

| ID | 제목 | 종류 | 데이터 |
|---|---|---|---|
| `chart-class` | Class distribution | donut | filtered |
| `chart-meshq` | Mesh quality | h-bar | filtered |
| `chart-lvl-class` | Level × Class | heatmap | filtered |
| `chart-vol` | Volume histogram | log10 hist | filtered |
| `chart-xy` (wide) | 2D footprint XY centroid | scatterGL | filtered, color mode |
| `chart-z` | Z height histogram | hist | filtered |
| `chart-pipeline` | Top 15 pipelines | h-bar | filtered |
| `chart-hubs` | Top 15 producer hubs | h-bar | filtered |
| `chart-pair-class` | Producer edges by class pair | stacked h-bar | **precomputed** (slicer 무관) |
| `chart-npd` | Top 15 NPD | h-bar | filtered |
| `chart-itype` | Top 15 항목\|유형 | h-bar | filtered |
| `chart-dwt-cls` (wide) | Dry weight by class | stacked h-bar | filtered |
| `chart-pmax` | Design max pressure | hist | filtered |
| `chart-tmax` | Design max temperature | hist | filtered |
| `chart-len` | Length histogram | hist | filtered |
| `chart-tri` | Mesh richness (log10 triangles) | hist | filtered |
| `chart-sched-levels` | Synthetic schedule by level | dual-axis bar | **precomputed** |
| `chart-sched-compare` (wide) | Schedule strategy comparison | dual h-bar | **precomputed** |
| `chart-sched-heavy` | Top 15 heaviest synth tasks | h-bar | precomputed |
| `chart-timeline` (wide) | Created vs Modified timeline | grouped bar | **precomputed** |

### 8.5 필터링된 객체 테이블 (Tabulator, 최대 2,000 행)

컬럼 (16개): id / name / class / lvl / pipeline / category / vol m³ / diag m / deg / status / material / npd / dry kg / tri / **rank** / **task** / mesh / giant.

각 컬럼 헤더에서 추가 input/list 필터 가능, 정렬 가능, 컬럼 순서 드래그 가능, 페이지당 20/50/100/500 행.

---

## 9. 검증된 인사이트 (값 + 출처)

각 인사이트는 dashboard 에서 직접 재현할 수 있는 슬라이서 조합 + 정확한 숫자를 함께 기록.

### 9.1 BIM 워크플로 — 1.3 % 만 승인 완료
| 항목 | 값 |
|---|---|
| Working | 7,174 (61.5 %) |
| Approved | **161 (1.3 %)** |
| LightPart | 48 |
| 빈값 | 4,626 (38.5 %) |
**재현**: Status 슬라이서 → Approved 만 체크 → Filtered Objects = 161.

### 9.2 컨테이너 — 27.9 % 가 실제 부품 아님
| 항목 | 값 |
|---|---|
| SKIP_CONTAINER | **3,353 (27.9 %)** |
| 검증 (3 독립 카운트 일치) | connected_groups singletons / validation AdjacencyCount=0 / Verdict=SKIP_CONTAINER 모두 정확히 3,353 |
**재현**: Mesh Quality 슬라이서 → skipped_container 만 → 3,353.

### 9.3 거대 단일 그룹 — 71.8 %
| 항목 | 값 |
|---|---|
| Giant component size | **8,626 객체 (71.8 %)** |
| 두번째 그룹 | 30 객체 |
**재현**: In Giant Group → yes → 8,626.

### 9.4 항목\|유형 collapse — 65.7 %
| 항목 | 값 |
|---|---|
| "Geometry Group" | **7,890 (65.7 %)** |
| "Geometry" | 145 |
| "Insulation Volume" | 145 |
**재현**: Top 15 항목\|유형 차트 1 위 — Producer 가 raw 카테고리를 단일 버킷에 collapse 하고 있다는 직접 증거 (memory plan #7).

### 9.5 단일 작성자 88 %
| 항목 | 값 |
|---|---|
| INGRNET\\SP3DAdminUser1 | **6,511 / 7,335 (88.8 %)** |
| 두번째 (PipingUser1) | 360 |
**재현**: User Last Modified 슬라이서.

### 9.6 모델링 burst — 2009-2016
| 항목 | 값 |
|---|---|
| 날짜 커버리지 | 7,382 / 12,009 (61.5 %) |
| 월 분포 | 30 distinct months |
| Range | 2009-01 ~ 2025-06 |
| 큰 burst | 2009-01 (1,064 created), 2016-12 (~700 created+modified) |
**재현**: Created vs Modified timeline 차트 — 두 burst 사이에 quiet period.

### 9.7 NPD 표준 분포
| Top NPD | 객체 수 |
|---|--:|
| 4in × 4in | 531 |
| 8in × 8in | 506 |
| 6in × 6in | 376 |
| 2in × 2in | 355 |
**재현**: Top 15 NPD 차트 또는 NPD 슬라이서.

### 9.8 백엔드 grouping 의 unassigned 함정
| groupBy | tasks | unassigned 비율 |
|---|--:|--:|
| Class | 5 | 49 % (Other 5,917) |
| ConstructionType | 3 | 71 % |
| Pipeline | 158 | **76 %** (9,083 / 12,009) |
| SystemPath | 3,369 | 35 % |
| **synth (level × class × package)** | **6,721** | **0** |
**재현**: Schedule strategy comparison 차트 — 빨간 막대가 모든 백엔드 grouping 에서 보임, synth 만 0.

### 9.9 Mesh 풍부도 — Ladder/Handrail 가 가장 복잡
| Top mesh | triangles |
|---|--:|
| LadderA1-1-0002 | 16,806 |
| LadderA1-1-0003 | 16,806 |
| LadderA1-1-0201 | 14,164 |
| TMHandrail-1-0202 | 14,028 |
**재현**: 테이블에서 `tri` 컬럼 desc 정렬. 설계자가 rung 하나하나를 분리 모델링했다는 증거.

### 9.10 Producer 인접 — 35.4 % precision vs 백엔드 AABB
| 항목 | 값 |
|---|---|
| Producer edges | 110,173 |
| 백엔드 AABB edges | 266,279 |
| 교집합 | 94,326 |
| Precision (백엔드 → producer) | 35.4 % |
| Recall (백엔드 → producer) | 85.6 % |
**해석**: 백엔드의 AABB 자체분류는 producer mesh-based adjacency 보다 측정 가능하게 worse — memory plan #2 의 근거.

---

## 10. 재현 절차 (Quick start)

새 PC 에서 이 dashboard 를 처음부터 만드는 단계:

```bash
# 0. 사전 조건
#    - Python 3.10+ (stdlib only, no pip install needed)
#    - .NET 8 SDK (백엔드 빌드용)
#    - Git clone 한 ontology-for-cm repo
#    - data/raw/dxtnavis/2026-04-07/ 가 존재 (raw export)

cd "C:/Users/Yoon taegwan/Desktop/AWP_2025/개발폴더/ontology-for-cm"

# 1. 백엔드 시작 (별도 터미널)
cd semantic-backend/src/SemanticBackendMock
dotnet run --no-launch-profile --urls "http://127.0.0.1:5050"
# → "Now listening on: http://127.0.0.1:5050"

# 2. Bundle import — refining + schedule + neo4j 를 한 번에
curl -X POST http://127.0.0.1:5050/dxtnavis/bundle/import \
  -H "Content-Type: application/json" \
  -d '{"exportDirectoryPath":"2026-04-07"}'
# → 응답에 refining/schedule/neo4j run id 들 (≈10s)

# 3. (선택) Pipeline 그루핑 schedule 추가 — backend_schedules 비교용
curl -X POST http://127.0.0.1:5050/dxtnavis/schedule/generate \
  -d '{"groupBy":"Pipeline","sortBy":"DisplayName","sortOrder":"asc","exportCsv":true}' \
  -H "Content-Type: application/json"
curl -X POST http://127.0.0.1:5050/dxtnavis/schedule/generate \
  -d '{"groupBy":"SystemPath","sortBy":"DisplayName","sortOrder":"asc","exportCsv":true}' \
  -H "Content-Type: application/json"
curl -X POST http://127.0.0.1:5050/dxtnavis/schedule/generate \
  -d '{"groupBy":"ConstructionType","sortBy":"DisplayName","sortOrder":"asc","exportCsv":true}' \
  -H "Content-Type: application/json"

# 4. dashboard 데이터 빌드
python scripts/analysis/260407/build_dashboard_data.py
# → dashboard_data.json + dashboard_data.min.json

# 5. (선택) 단일 HTML 배포 파일
python scripts/analysis/260407/build_standalone.py
# → dashboard_standalone.html (8.4 MB self-contained)

# 6. (선택) Navisworks Timeliner CSV
python scripts/analysis/260407/build_timeliner_csv.py
# → data/working/dxtnavis/timeliner/synth_timeliner.csv

# 7. 브라우저에서 보기
cd scripts/analysis/260407
python -m http.server 9001 --bind 127.0.0.1
# → http://127.0.0.1:9001/dashboard.html

# 8. 백엔드 종료
taskkill //F //IM dotnet.exe   # Windows
# 또는 백엔드 터미널에서 Ctrl+C
```

**모든 단계 합쳐 약 1분.** 결과는 본 문서의 §9 의 모든 숫자가 그대로 재현됩니다.

---

## 11. 알려진 한계 및 의도적 미적용

### 11.1 단위 정규화 안 함
`Length`, `Dry Weight`, `Design P/T` 등 수치 컬럼은 **mm/m, kg/t, psi/bar 가 섞여 있을 수 있음**. 차트 hint 에 "as-imported" 명시. 히스토그램이 명백히 bimodal 이면 v2 에서 unit map 추가 필요.

### 11.2 Calendar 매핑은 평균 압축
`cal_start = cumulative_mh_days / CREW_PARALLELISM` 은 12 크루가 균등 부하 분산했을 때의 평균값. 실제 round-robin 할당이 아니라 단순 압축. 개별 task 의 정확한 crew assignment 가 필요하면 별도 scheduler 필요.

### 11.3 Producer 인접의 일부 hub 는 분석용 가상 객체
가장 큰 hub (degree 5,267) 가 "Obstruction Volume" 같은 분석용 객체. memory plan #3 의 blacklist 는 아직 적용 안 함.

### 11.4 신뢰할 수 없는 백엔드 필드
- `SourceFileName` : refining 채움률 0.008 % (백엔드 파싱 버그 — memory plan #6). 대신 `SourceFilePath` (99.99%) 사용.
- 153 / 660 Equipment 객체에 빈 `EquipmentName` (memory plan #6).

### 11.5 Dashboard 가 의도적으로 안 읽는 데이터
| 데이터 | 이유 |
|---|---|
| `spatial_relationships.ttl` (48.6 MB RDF) | adjacency.csv 가 동일 정보를 더 단순하게 제공 |
| `neo4j/` CSV | Neo4j 인스턴스에 별도 import 해야 의미 있음 |
| AllProperties `재질\|광택/반사/...` 13 RGB float | 시각화 무가치 |
| AllProperties `Iso Sheet No`, `Spool` | 거의 빈값 |
| `형상\|삼각형` | mesh triangle 카운터 아니라 Navisworks 내부 scene graph 카운터 (이름 동일하지만 의미 다름) |
| `tessellation_failures.csv` | mesh/validation 에서 이미 커버 |

### 11.6 데이터에 없는 정보 (외부 입력 필요)
- 실제 calendar 날짜 (Master schedule 필요)
- Crew/협력사 배정 (PM 의사결정)
- CPM logical predecessor/successor (논리적 의존)
- 단위 시공 인공 (man-hour) 의 정확한 산업 표준값
- BIM 360 / Navisworks 외부 sync 상태

---

## 12. 산출물 인벤토리 (현재)

### 12.1 백엔드 산출물 (재실행 가능)
```
data/working/dxtnavis/
  dxtnavis-semantic.db                258.3 MB   SQLite store
  refining/dxtref-*/                  5 runs · latest 69.5 MB
  schedule/dxtsch-*/                  9 runs · 4 grouping types
  neo4j/dxtneo-*/                     5 runs (unused by dashboard)
  timeliner/                          NEW today
    synth_timeliner.csv               1.0 MB · 6,721 task rows
    synth_task_objects.csv          516.0 KB · 12,009 links
```

### 12.2 Dashboard 산출물
```
scripts/analysis/260407/
  build_dashboard_data.py             Python builder (stdlib only)
  build_standalone.py                 Standalone bundler
  build_timeliner_csv.py              Timeliner exporter
  dashboard_data.json                12.3 MB   pretty
  dashboard_data.min.json             8.3 MB   compact (fetched)
  dashboard.html                     63.4 KB   UI source
  dashboard_standalone.html           8.4 MB   shareable single file
  level1..6_*.py                      baseline analysis scripts
  build_powerbi_bundle.py             Power BI star schema bundler
  powerbi_inventory.py                Power BI suitability inventory
```

### 12.3 문서
```
docs/analysis/
  dxtnavis-2026-04-07-baseline-insights.md      9 인사이트, ranked follow-ups
  dxtnavis-2026-04-07-powerbi-integration.md    Power BI 통합 가이드
  dxtnavis-2026-04-07-dashboard-master.md       이 문서
docs/tech-specs/
  dxtnavis-bundle-import-spec.md                백엔드 bundle import 스펙
docs/testing/
  DXTNAVIS-SEMANTIC-PIPELINE-TEST.md            백엔드 테스트 절차
docs/status/
  PLAN-TRACKER.md                               DXTnavis 파이프라인 plan items
```

---

## 13. 다음 단계 후보 (참고)

이 문서를 기준으로 다음 작업이 가능합니다:

1. **Gantt 차트** — synth_tasks 의 start/end 를 timeline bar chart 로 시각화 (Plotly bar mode + base offset)
2. **Progress animation** — Schedule rank slider 자동 재생 (시간 흐름대로 객체가 나타나는 애니메이션)
3. **Backend schedule_key 이식** — C# 백엔드에 동일 composite key 로직 추가하여 SQLite store 에 영구 저장 (memory plan #4 의 진화)
4. **Crew load 시각화** — 12 크루 round-robin 할당 + crew 별 utilization 차트
5. **단위 정규화 v2** — 수치 컬럼의 mm/m, kg/t, psi/bar 자동 감지 + 정규화
6. **Obstruction Volume 블랙리스트** — memory plan #3 의 blacklist 를 빌더에 적용
7. **Other → Container/Uncategorized 분리** — memory plan #1 (백엔드 변경 필요)
8. **다음 export 자동 처리** — `data/raw/dxtnavis/<날짜>/` 가 들어오면 위 §10 의 단계들을 한 스크립트로 자동화

---

## 14. 부록 — 핵심 코드 위치 빠른 참조

| 기능 | 파일 | 라인 (대략) |
|---|---|---|
| 백엔드 schedule generation 라우트 | `semantic-backend/src/SemanticBackendMock/Program.cs` | 530-541 |
| 백엔드 schedule 핵심 알고리즘 | `Services/DxtnavisSemanticStore.cs` | 426-613 |
| 백엔드 ResolveFieldValue (groupBy 처리) | `Services/DxtnavisSemanticStore.cs` | 1642-1666 |
| Dashboard 빌더 main | `scripts/analysis/260407/build_dashboard_data.py` | `def main()` |
| Korean datetime parser | `build_dashboard_data.py` | `parse_korean_datetime` |
| Synth schedule key | `build_dashboard_data.py` | `_package_for`, `_priority_for` |
| Duration estimation | `build_dashboard_data.py` | `_task_duration_days` + `MH_PER_KG` |
| Backend schedule scan | `build_dashboard_data.py` | `agg["backend_schedules"]` 블록 |
| Dashboard apply filters | `dashboard.html` | `function applyFilters()` |
| Scatter color modes | `dashboard.html` | `function renderScatterXY()` |
| Schedule comparison chart | `dashboard.html` | `function renderSchedCompare()` |
| Standalone bundler | `scripts/analysis/260407/build_standalone.py` | inject `<script>window.__DXTNAVIS_DATA = ...</script>` |
| Timeliner exporter | `scripts/analysis/260407/build_timeliner_csv.py` | `def main()` |

---

## 15. 메모 — 이 문서의 갱신 시점

이 문서는 **2026-04-10** 시점 dashboard 의 스냅샷입니다. 다음 조건 중 하나라도 발생하면 갱신해야 합니다:

- 새 export (`data/raw/dxtnavis/<다른날짜>/`) 추가 → §10 재실행 + 숫자 갱신
- `build_dashboard_data.py` 의 가정 변경 (CREW_PARALLELISM, ZONE_X, MH_PER_KG, ...) → §6 가정 표 갱신
- 새 KPI / 차트 / 슬라이서 추가 → §8 인벤토리 갱신
- 백엔드 schedule grouping 알고리즘 변경 → §4.5 + §6 갱신
- 새 인사이트 발견 → §9 추가
- memory plan 의 plan items (#1~#7) 중 어느 하나라도 적용 → §11 한계 표 갱신

문서 길이: 약 1,200 줄. 새 개발자가 이 문서 + repo 만 가지고 1 시간 이내에 동일한 dashboard 를 복원할 수 있어야 합니다.
