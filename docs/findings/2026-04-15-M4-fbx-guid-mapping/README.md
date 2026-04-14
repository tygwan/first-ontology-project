# 2026-04-15 — M4 — gap_fallback.fbx 의 GUID 가 한국어 property 에 숨어 있음

**Severity**: 🟠 MAJOR
**Status**: 🟡 **Partially Resolved** (740/788 바인더블, 48 은 DXTnavis 수정 대기)
**Discovered by**: `fbx_supplemented` 객체들의 `mesh_uri` 가 존재하지 않는 GLB 파일을 가리킴 — 원인 추적 조사
**Affects**: Gold `mesh_quality = fbx_supplemented` 788 객체, 3D 시각화 파이프라인, Foundry 시각 QA, adjacency 간선 9.4%

---

## 1. 현상 (Symptom)

Gold layer 의 788 객체 (`mesh_quality = "fbx_supplemented"`) 는 `mesh_uri` 가 지정되어 있지만 해당 GLB 파일이 디스크에 존재하지 않음. DXTnavis 는 tessellation 실패 객체를 위해 **단일 `gap_fallback.fbx` (23 MB)** 에 묶음 export 를 수행하나, 그 FBX 내부의 mesh → Gold `object_id` 매핑 메커니즘이 문서화되어 있지 않았음.

**정량 영향**:
- 788 객체 (Gold 12,009 중 6.6%) 는 기하 소스가 모호한 상태로 Gold 에 기록됨
- 이 객체들은 주로 **Flange / Plate / Weldolet** 같은 **물리적 연결 부품**
- adjacency 그래프의 **20,746 간선 (9.4%)** 가 이 788 객체를 한쪽 이상 끝점에 포함
- Pipeline 142개 중 **40개 (28.2%)** 는 이 객체들을 제거하면 Graph 가 분절됨
- **64 개가 Articulation point (cut vertex)** — 제거 시 연결 성분이 늘어남

**체감 가능한 예**: `Flange-2101` (U12 의 0046 라인) 이 mesh 없이 점으로만 표시됨 → 정비 시뮬레이션에서 볼트 위치가 안 보임.

## 2. Evidence

**FBX 구조 덤프 요약** (binary parser + `항목 - GUID` property grep):

| 지표 | 값 |
|------|---:|
| FBX 파일 크기 | 23.0 MB |
| Mesh Model 노드 수 | **788** (Gold `fbx_supplemented` 와 완전 일치) |
| Properties70 `"항목 - GUID"` 보유 | **740 (93.9%)** |
| Properties70 GUID 미보유 (이름 = `"Geometry"`) | **48 (6.1%)** |
| 48 객체의 `vertex_count` | 전부 1728 (동일 템플릿) |
| 48 객체의 bbox | 전부 0.07 × 0.19 × 0.19 m (플랜지 크기) |

**좌표계 mismatch**:

| 축 | FBX range | Gold range | 결론 |
|----|-----------|-----------|------|
| x | [-51.0, -1.52] | [+1.52, +50.98] | **X 축 반전** (LH vs RH) |
| y | ≈ [0, 200] | ≈ [0, 200] | 일치 |
| z | ≈ [0, 200] | ≈ [0, 200] | 일치 |

→ Centroid 기반 fallback 매칭은 `fbx_x = -gold_x` 변환 후 수행해야 함.

**FBX Properties70 에서 발견한 per-object 메타** (Gold 에 없음):

| Property | 설명 | 활용 가능성 |
|----------|------|-------------|
| `sp3d_moniker` | SP3D 내부 ID (`@a=0027!!80005##...`) | Cross-system linkage |
| `sp3d_display_name` | 노드의 사람용 이름 | UI 라벨 |
| `sp3d_system_path` | `TRAINING\A1\U12\Process\Pipelines\...` | 계층 검증용 |
| `sp3d_bom_desc` | BOM 설명 (예: `0.38 in Plate Steel, 8.00 in X 8.00 in 4 eq spaced 0.69 in dia. holes`) | 자재 BOM, 중량 계산 |
| `sp3d_support_weight` | 중량 (예: `13.68 lbm`) | Structural load |
| `sp3d_status` | `Working / Held / ...` | Lifecycle gate |
| `sp3d_construction_type` | `New / Existing / Demolish` | 시공 순서 분석 |
| `sp3d_support_location` | `E 141 ft 7 in  N 478 ft 10 in  EL+ 10 ft 2 in` | Survey coord 검증 |

**증거 파일**:
- [`evidence/mapping.csv`](evidence/mapping.csv) — 788 mesh 전체 (740 GUID + 48 `Geometry`)
- [`evidence/48_fbx_missing_guid.csv`](evidence/48_fbx_missing_guid.csv) — FBX 측 48 개 generic Geometry 노드
- [`evidence/48_unmatched.csv`](evidence/48_unmatched.csv) — Gold 측 48 개, centroid 매칭 결과 (distance + confidence)

## 3. Analysis

### 3.1 Root cause

`gap_fallback.fbx` 는 DXTnavis 의 Navisworks → FBX export 단계에서 생성되며, 각 Mesh Model 노드가 `Properties70` 블록 안에 SP3D 원본 메타를 기록함. 그러나:

1. **GUID 키가 로컬라이즈되어 있음**: 키 문자열이 `"항목 - GUID"` (Korean — "Item - GUID") 로 기록됨. DXTnavis 가 Navisworks API 에서 Korean-localized 프로퍼티 이름을 그대로 전달한 것으로 추정. 영어 `"Item - GUID"` 나 ASCII 매핑은 전혀 없음.
2. **48 개의 "generic" Geometry 노드에는 GUID 가 빠짐**: 이름이 `"Geometry"` 이고, SP3D 메타 필드(`sp3d_moniker`, `sp3d_display_name` 등) 가 모두 공백. DXTnavis 가 Flange 인스턴스 하나를 **템플릿 참조** 로 기록한 뒤 GUID 를 붙이는 것을 누락한 것으로 보임.

### 3.2 왜 이전에 발견 안 됐는가

- Phase 1a 에서는 `geometry.csv` 의 tessellation 실패 플래그만 확인했고, `gap_fallback.fbx` 의 내부 구조는 살피지 않음
- `mesh_uri` 가 지정되어 있었기에 "생성됨" 으로 간주하고 디스크 확인을 건너뜀 (R9 provenance 의 side effect — raw 는 검증했으나 derived 생성물 검증 누락)
- 기존 R3 findings (M1, M2, M3) 는 구조/adjacency 쪽에 집중되어 있었음 — 기하 파이프라인은 blind spot

### 3.3 임팩트가 왜 큰가 (구조적 중요도)

이전 세션 (Phase 4 graph analytics) 에서 측정:

| 지표 | 값 | 해석 |
|------|----:|------|
| 788 객체가 관여한 adjacency 간선 | 20,746 (9.4%) | 무시할 수 없는 비율 |
| 제거 시 분절되는 pipeline | 40 / 142 (**28.2%**) | 가장 분절이 큰 사례: P-10147 (7→24 컴포넌트) |
| Articulation point (cut vertex) | 64 | graph 연결성을 지탱하는 관절 |
| 주요 클래스 | Flange, Plate, Weldolet | **물리적 연결/접합 부품** |

→ 이들은 "시각화가 안 보여도 되는 장식" 이 아니라 **파이프라인 위상 (topology) 을 지탱하는 핵심 연결자**. 시공 순서 / 정비 / 부속품 BOM 어느 관점에서든 누락 시 공정 해석이 왜곡됨.

### 3.4 DXTnavis 측 논의 필요 사항

| 요청 | 이유 |
|------|------|
| `"항목 - GUID"` → `"sp3d_object_id"` 로 키 재명명 (또는 영문 별칭 동시 기록) | 로케일 독립 |
| 48 generic Geometry 노드에도 GUID 기록 | Flange 템플릿 인스턴스도 individual object 이므로 GUID 필수 |
| **Sidecar index 파일** (`gap_fallback.fbx.index.csv`) 동시 export | binary FBX 파싱 없이 매핑 |
| FBX 좌표계 변환 행렬 매니페스트 기록 | X 반전 원인이 Navisworks 인지 DXTnavis 인지 명시 |
| `manifest.json` 에 `fbx_mesh_count: 788` + `fbx_guid_coverage: 0.939` 등 통계 기록 | 다운스트림 무결성 체크 |

## 4. Resolution

### 4.1 접근: Binary FBX parsing + 2-stage binder

Raw 데이터 (`gap_fallback.fbx`) 는 변경하지 않음 (R9 provenance). 대신:

1. **Stage 1 (GUID-based, 740 객체)**: FBX binary 에서 `"항목 - GUID"` 속성을 직접 파싱하여 `object_id` 추출 → Gold `object_id` 와 1:1 조인.
2. **Stage 2 (centroid-based, 48 객체)**: 이름이 `"Geometry"` 이고 GUID 가 없는 mesh 들은 **X 축 반전 변환 후 centroid distance** 로 최근접 Gold 객체에 매칭. 현재 48 개 전원 `confidence = "likely" or "ambiguous"` — 대부분 거리가 크고 같은 파이프라인 안에 다수 후보가 있어 자동 매칭 신뢰도 낮음.

→ **Stage 2 는 DXTnavis 측 수정으로 해결하는 것이 맞음.** 우리는 740 개는 자동, 48 개는 수동 또는 DXTnavis PR 수령 후 처리로 분리.

### 4.2 Action items

- [x] FBX 구조 역공학 + 788 mesh 식별
- [x] `"항목 - GUID"` property 파싱 로직 작성 → 740 매칭
- [x] 48 generic Geometry 노드의 속성 vs Gold 속성 비교
- [x] 좌표계 mismatch 식별 (X 반전)
- [x] Centroid matching (confidence 포함) 생성 → `evidence/48_unmatched.csv`
- [x] `audit.py` 재현 스크립트 작성 → 이 폴더
- [x] `evidence/mapping.csv` 에 740 + 48 통합 export
- [x] Finding 아카이브 (이 문서)
- [x] DXTnavis PR 초안 작성 ([`dxtnavis-pr-draft.md`](dxtnavis-pr-draft.md)) — localized property key + missing GUID + sidecar index + X 축 반전
- [ ] DXTnavis Issue/PR 제출 (upstream)
- [ ] `bimkg.ingest.fbx` 모듈 신설 → Gold `mesh_uri` 를 `gap_fallback.fbx#mesh_index=N` 형태로 재작성
- [ ] Foundry `fbx_mesh_index` 컬럼 추가 (다운스트림 3D 뷰어 용)
- [ ] 48 객체는 임시로 `mesh_quality = "fbx_unbindable"` 로 강등 및 `K5` Known limitation 으로 기록

### 4.3 재발 방지 (Prevention)

1. **Upstream (DXTnavis)**: sidecar `gap_fallback.fbx.index.csv` 를 동시 export 하면 로컬라이즈 문제 · 파서 재발명 · coord 변환 혼동 모두 해소. Issue 제출 예정.
2. **Local (this repo)**: `verify_phase1.py` 에 **"모든 `mesh_uri` 가 실제 파일을 가리키는지"** 체크 추가. Gold 생성 시 `fbx_supplemented` 카운트를 `gap_fallback.fbx` 의 mesh model 카운트와 대조하는 assertion.
3. **Docs**: `docs/reference/dxtnavis-2026-04-07-baseline-insights.md` 에 "FBX 내부 구조 리버스엔지니어링 결과" 섹션 추가 예정.

## 5. References

- **FBX 원본**: `data/backup/260415 최신 glb/dxtnavis_export_20260415_044932/gap_fallback.fbx` (23 MB)
- **Gold 데이터**: `data/enriched/2026-04-12/bim_objects.parquet` — 필터 `mesh_quality == "fbx_supplemented"` → 788 rows
- **재현 스크립트**: [`audit.py`](audit.py) — bimkg 환경 통합 (Gold cross-check 포함)
- **Upstream PR demo**: [`fbx_parser_demo.py`](fbx_parser_demo.py) — stdlib only, DXTnavis PR 첨부용
- **DXTnavis PR 초안**: [`dxtnavis-pr-draft.md`](dxtnavis-pr-draft.md) — 4 issue + alternative 1 (individual GLB) 제안
- **증거 CSV**: [`evidence/mapping.csv`](evidence/mapping.csv), [`evidence/48_unmatched.csv`](evidence/48_unmatched.csv), [`evidence/48_fbx_missing_guid.csv`](evidence/48_fbx_missing_guid.csv)
- **시각화**: [`figures/coverage_distribution.png`](figures/coverage_distribution.png), [`figures/adjacency_impact.png`](figures/adjacency_impact.png), [`figures/pipeline_fragmentation.png`](figures/pipeline_fragmentation.png)
- **Figure 생성 스크립트**: [`make_figures.py`](make_figures.py)
- **관련 finding**:
  - M3 (parent box contamination) — adjacency 오염의 구조적 원인; M4 는 adjacency 의 "누락된 노드" 관점
  - M2 (adjacency tiers) — fbx_supplemented 객체는 주로 Strong tier 의 endpoint (Flange = 볼트/용접)
- **상위 맥락**: `docs/PROJECT-JOURNAL.md` §3 M4
