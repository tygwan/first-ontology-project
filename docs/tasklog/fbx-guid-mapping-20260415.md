# FBX GUID Mapping — 100% fbx_supplemented 매핑 달성

**작업일**: 2026-04-15
**관련 Finding**: M4 (docs/findings/2026-04-15-M4-fbx-guid-mapping/)
**관련 컴포넌트**: `src/bimkg/ingest/` (예정), `data/backup/260415 최신 glb/`

---

## 1. 언어/내용 (What)

Python 3.12 환경에서 `gap_fallback.fbx` (23 MB binary FBX)를 파싱해 **788개 fbx_supplemented 객체 전체를 Gold layer의 `object_id`와 1:1 매핑**하는 작업.

- 788 Mesh Model이 FBX 내부에 번들되어 있음
- 기존 Gold의 `mesh_uri` 컬럼은 이들을 참조하지만 개별 GLB 파일이 없어서 3D viewer에서 누락
- Palantir Foundry 3D 통합을 위해 개별 GLB export가 필요하고, 그 전제로 ObjectId 매핑이 필요

**사용 도구**: `assimp-py==1.1.0`, `pygltflib`, `numpy`, `scipy.optimize.linear_sum_assignment`, 커스텀 바이너리 FBX 파서

---

## 2. 문제 (Problem)

### 2.1 FBX 포맷 파서 부재
- Python 3.12 환경에서 `bpy` (Blender module)가 3.11/3.13만 지원 → 설치 실패
- `trimesh`는 FBX 미지원 (assimp 백엔드 필요)
- 시스템에 `libassimp-dev`, `blender` CLI, `assimp` CLI 모두 부재

### 2.2 매핑 메타데이터 숨김
- FBX 노드 이름은 `display_name` ("Flange-2101", "Aspects", "Utility_FOUR_HOLE_PLATE_4-1-C8")
- 다수 중복 ("Flange-1701" × N개, "Aspects" × 많음)로 노드 이름만으론 1:1 매핑 불가

### 2.3 좌표계 불일치
- FBX centroid 범위: x=[-51.00, -1.52], y=[0.52, 8.60], z=[-1.56, 146.36]
- Gold centroid 범위: x=[1.52, 50.98], y=[-1.52, 146.36], z=[0.52, 8.59]
- 축 부호·순서가 다른 좌표계 (초기 centroid 매칭 시 평균 거리 197m, 무의미)

---

## 3. 분석 (Analysis)

### 3.1 FBX binary 구조 직접 탐색
`strings` + `grep`으로 FBX 내부 문자열 분석:

- **802개 GUID** 발견 (전체 FBX 바이너리 내)
- 모든 GUID 앞에 공통 패턴: `GUIDS....KStringS....S....US$...`
  - 이는 FBX Properties70 블록의 P 노드 포맷:
    `P("<property_name>", "KString", "", "U", "<guid_string>")`
- 바이너리 분석에서 property_name이 한국어 **"항목 - GUID"** (SP3D Korean localization)

### 3.2 커스텀 FBX 바이너리 파서 구현
`assimp-py` (1.1.0) 설치 성공 → 씬 로드 가능. 하지만 ObjectId는 assimp가 기본 제공하지 않음 (FBX custom property는 접근 어려움).

→ `struct`로 FBX 바이너리 노드 트리 직접 파싱:
- 64-bit offset (FBX 7500+)
- `Objects` 섹션 → `Model` 노드 필터 (type="Mesh")
- 각 Model 내부 `Properties70` > `P` 노드 순회
- `P` 노드의 첫 property = name, 매칭 시 `"항목 - GUID"` value 추출

**결과: 740/788 (93.9%) 매핑 성공**

### 3.3 48개 누락 원인 분석
누락된 48개 조사:
- 전부 FBX 노드 이름 = `"Geometry"` (generic fallback 이름)
- 전부 `Properties70`에 `"항목 - GUID"` 속성 **자체가 부재**
- 전부 `SmartPlant 3D - *` 속성도 부재
- 모두 `vertex_count = 1728`, `bbox = 0.07 × 0.19 × 0.19 m` (Flange template 기하)
- Gold에서도 동일 48개가 `display_name = "Geometry"`

→ **DXTnavis 업스트림 버그**: 이 48개는 SP3D 속성 copy 단계에서 GUID가 누락됨.

### 3.4 좌표계 변환 공식 탐색
9가지 변환 실험 (Hungarian optimal assignment 기준):

| Transform | Total cost | Max dist | Median |
|---|---|---|---|
| Identity | 9459.66 | 218.63 | 212.42 |
| x 부호 반전 | 8707.49 | 206.01 | 197.27 |
| yz 교환 | 3552.56 | 101.98 | 77.65 |
| **x-반전 + yz 교환** | **1.02** | **0.15** | **0.017** |

**공식**: `Gold(x, y, z) = (-FBX.x, FBX.z, FBX.y)`

- FBX: Z-up 좌표계 + X 미러링 (SP3D C# 관례)
- Gold: Y-up 오른손 좌표계 (geometry.csv 표준)

### 3.5 48개 최종 매칭
변환 적용 후 Hungarian assignment:
- min=0.013m, median=0.017m, max=0.147m
- 47/48이 < 0.1m (부동소수점 오차 수준)
- 1개만 0.15m (여전히 동일 객체 확실)

---

## 4. 해결 (Solution)

### 4.1 하이브리드 매핑 전략

```
Phase 1: 740개 — FBX Properties70 > "항목 - GUID" 추출
  ├─ Method: fbx_properties70_guid
  └─ Confidence: exact

Phase 2: 48개 "Geometry" — 좌표 변환 + Hungarian assignment
  ├─ Method: centroid_hungarian_xform
  ├─ Transform: (x, y, z) → (-x, z, y)
  └─ Confidence: high (47/48 < 0.1m), medium (1/48 = 0.15m)
```

### 4.2 최종 매핑 파일
`temp/fbx_mesh_mapping_final.{csv,parquet}` (788 rows × 11 cols)

**컬럼**:
- `mesh_index` — FBX 씬 내부 인덱스
- `object_id` — Gold의 GUID (매핑 키)
- `match_method` — 매칭 방법
- `match_confidence` — exact / high / medium
- `match_distance_m` — centroid 거리 (48개에만)
- `sp3d_moniker`, `sp3d_display_name`, `sp3d_system_path`, `sp3d_bom_desc`, `sp3d_support_weight`, `sp3d_status` — FBX에서만 추출된 SP3D 메타데이터 (740개에만)

### 4.3 부가 산출물
- FBX 파싱 과정에서 **Gold에 없던 SP3D 속성 7종** 발견 (sp3d_moniker, sp3d_system_path, sp3d_bom_desc, sp3d_support_weight, sp3d_status, sp3d_construction_type, sp3d_support_location)
- 향후 Gold에 merge 가능 (`add_fbx_metadata()` 함수 추가 예정)

### 4.4 향후 작업 (분리)
1. **DXTnavis PR**: 48개 Geometry 객체에 GUID 포함 요청 + 한국어 property name 개선 + 사이드카 index 파일 제안
2. **개별 GLB export**: assimp_py로 788개 mesh → 788개 GLB 파일 분리
3. **좌표계 변환 적용**: GLB export 시 (x, y, z) → (-x, z, y) 변환으로 Gold와 정합
4. **Gold merge**: SP3D 메타데이터 7종을 `clean.py`에 통합

---

## 5. 결과 (Result)

### 5.1 달성 지표

| 지표 | Before | After |
|---|---|---|
| fbx_supplemented 매핑 | 0/788 (0%) | **788/788 (100%)** |
| 정확 매칭 (exact) | 0 | 740 |
| 고신뢰 매칭 (high) | 0 | 47 |
| 중신뢰 매칭 (medium) | 0 | 1 |
| FBX 신규 메타데이터 | 0 | 7종 × 740 객체 |
| 좌표계 변환 공식 | 미확인 | `(-x, z, y)` 확립 |

### 5.2 검증 기록
```
Mesh Model 총: 788
FBX Properties70 GUID 추출: 740
48개 누락 → Hungarian 매칭 완료
Gold fbx_supplemented: 788
매핑됨: 788
누락: 0
커버리지: 100.0%
```

### 5.3 재현 환경
- `assimp-py==1.1.0` (precompiled wheel)
- `pygltflib==1.16.5`
- `pandas==2.x` with `future.infer_string=False`
- `scipy.spatial.distance.cdist` + `scipy.optimize.linear_sum_assignment`
- 커스텀 FBX binary 파서 (docs/findings/2026-04-15-M4-fbx-guid-mapping/audit.py)

### 5.4 후속 이슈 (Open)
- **DXTnavis PR 제출** — 48 Geometry GUID 누락 (draft: docs/findings/2026-04-15-M4-fbx-guid-mapping/dxtnavis-pr-draft.md)
- **Step 2: 개별 GLB export** — 788개 → 788 GLB 파일 변환
- **Step 3: Gold에 SP3D 메타데이터 merge** — `clean.py`에 `add_fbx_metadata()` 추가
- **Step 4: mesh_uri 통합 + Foundry Media Set 업로드**
