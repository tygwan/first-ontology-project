# Session 2026-04-17 — Phase 2/3 Foundry Ontology Registration 완료

**일자**: 2026-04-17
**세션 유형**: AI FDE + local SDK 병행 디버깅 + 아키텍처 전환
**관련 Finding**: [M6 — Ontology registration asymmetry](../findings/2026-04-17-M6-ontology-registration-asymmetry/)

---

## 1. 언어 / 내용

### 시작 상태
- Phase 1 Interfaces 3개 등록 완료 (BimObject, HasSP3DMetadata, HasPressureTemp)
- BimStructural Object Type 만 등록 완료 (4,840 objects 로딩 중, mesh_uri=String)
- BimPiping 등록 시도 중 schema 조회 실패 → indexer `EntityTypesNotInitialized`
- 나머지 4개 Object Type (Equipment/Electrical/HVAC/Other) 미등록
- 2개 Aggregate Object Type (BimPipeline/BimPipeRun) 미등록
- 4개 Link Type (adjacentTo/hasParent/belongsToPipeline/inGroup) 미등록

### 종료 상태 — **완성**
- **BimObject** 통합 Object Type 등록 완료 (12,009 objects, refined_class 필터 기반)
- BimPipelines Object Type 등록 완료 (147 objects)
- BimPiping 별도 OT 보존 (3,062 objects, 62 properties)
- 4개 Link Type 전부 생성:
  - **Adjacent To** (BimObject↔BimObject, Many-to-Many, Join table)
  - **Has Parent / Children** (BimObject↔BimObject, Many-to-One, FK `parent_id`)
  - **In Group / Group Members** (BimObject↔BimObject, Many-to-One, FK `group_id`)
  - **Belongs To Pipeline** (BimObject→BimPipelines, Many-to-One, FK `sp3d_pipeline`)

### 생성된 Foundry 리소스

| 리소스 | 유형 | RID (신규) |
|---|---|---|
| `bim_piping` | Dataset (재생성) | `ri.foundry.main.dataset.19583834-1d30-471a-a25b-1b92f682fcb8` |
| `bim_piping_with_media_ref` | Dataset (Transform 출력) | (AI FDE 생성) |
| `bim_structural_with_media_ref` | Dataset | (AI FDE 생성) |
| `bim_equipment_with_media_ref` | Dataset | (AI FDE 생성) |
| `bim_electrical_with_media_ref` | Dataset | (AI FDE 생성) |
| `bim_hvac_with_media_ref` | Dataset | (AI FDE 생성) |
| `bim_other_with_media_ref` | Dataset | (AI FDE 생성) |
| `bim_objects` | Dataset (UNION) | `ri.foundry.main.dataset.7d5c883e-a60e-46d2-acbe-ea741447b129` |
| `bim-mesh-uri-transform` | Code Repo | (AI FDE 생성) |
| BimObject | Object Type | — |
| BimPipelines | Object Type | — |
| 4 Link Types | — | — |

### 로컬 코드 변경
- `data/ontology/2026-04-12/object_types/{piping,structural,equipment,electrical,hvac,other}.parquet`
  - `sp3d_sp3d_moniker` → `sp3d_moniker` 리네임 (6개 전수)
  - `piping.parquet` 에서 `mesh_uri` 의 `mesh/` prefix 제거 (후속으로 Foundry Transform 이 나머지 5개 처리)
- `scripts/rename_double_prefix_column.py` — 리네임 + 6개 재업로드 스크립트 (untracked, 부분 실행)
- `src/bimkg/ingest/exporters/foundry_upload.py:71-96` — `fix_dtypes_for_foundry` 로직 검증 (null Arrow dtype 방어)

---

## 2. 문제

BimPiping 등록 실패의 원인을 추적하는 과정에서 **5개 중첩 이슈** 가 순차적으로 드러남:

### 문제 1 — Parquet `null` Arrow dtype leak (기각)
- `piping.parquet` 에 64개 `null`-typed 컬럼 (전부 NaN → palantir-sdk 가 Arrow null 타입으로 직렬화)
- 가설: Foundry Funnel 이 null dtype 해석 실패 → schema resolve 실패
- **반증**: `structural.parquet` 은 51개 null-typed 컬럼 + 4개가 실제 매핑됐는데도 정상 작동 (4,840 objects 로딩) → null dtype 단독 원인 아님

### 문제 2 — Auto-import 170 properties 과다 (부분 원인)
- Ontology Manager 의 "Create Object Type" 마법사가 backing dataset 의 219개 컬럼 전부 자동 매핑
- spec 상 BimPiping = 63 properties / BimStructural = 59 / Equipment 53 / Electrical 51 / HVAC 50 / Other 45
- BimPiping, BimStructural 모두 ~170개 auto-map 된 상태 → 둘 다 이 상태인데 구조만 성공, piping 만 실패 → 이것도 단독 원인 아님

### 문제 3 — 컬럼명 이중 prefix (`sp3d_sp3d_moniker`)
- DXTnavis XLSX loader 의 버그로 `sp3d_` prefix 이중 부여 → 컬럼명 `sp3d_sp3d_moniker`
- Foundry camelCase 자동 매핑 (`sp3dMoniker` → `sp3d_moniker` 기대) 과 불일치 → 수동 매핑 필요
- 6개 Object Type dataset 전수 적용 필요

### 문제 4 — meshUri Interface property ID collision (결정적)
- Structural: interface property 가 `mesh_uri_BimObject` 로 **별도 property ID** 로 생성 (Media Reference 타입) + 로컬 `mesh_uri` (string) 공존
- Piping: `mesh_uri` 단일 property 가 **로컬 (string) + interface (Media Reference) 겸용** → 타입 충돌
- Funnel indexer 가 타입 resolve 실패 → `EntityTypesNotInitialized` 영구 고정

### 문제 5 — Media Reference path 불일치 (최종 blocker)
- Media Set `bim_mesh` 내 파일 경로: `UUID.glb` (prefix 없음, `upload_glb_to_foundry_mediaset.py:111` `media_item_path=f"{glb_path.stem}.glb"` 에 기인)
- Dataset `mesh_uri` 컬럼 값: `mesh/UUID.glb` (prefix 있음)
- Funnel 이 `mesh/UUID.glb` 를 Media Set 에서 찾지 못해 3,062 rows 전수 `Data Format Violation`

### 문제 6 — Cross-type Link Type 구성 불가
- `bim_adjacent_to` 는 6개 Object Type 간 교차 간선 110,173개
- Foundry Link Type 은 concrete Object Type 쌍에만 생성 가능 → 6×6=36 조합 비현실적
- 기존 6 specialized Object Type 구조 로는 해결 불가능

---

## 3. 분석

### 3.1 Phase 1 원설계 vs Cheatsheet 간 모순
- **계획 A** (`src/bimkg/ingest/exporters/foundry.py:23-34`): "all 216 columns — Foundry users decide filter at platform level"
- **계획 B** (`docs/plan/ontology-registration-cheatsheet.md:175`): "BimPiping = 63 properties 만 spec"
- Exporter 는 A 대로 219 cols parquet 생성 → Foundry UI auto-import → spec B 와 불일치
- **교훈**: 두 계획서가 병행 존재할 때 한쪽을 버리지 않으면 실행 시 혼란 발생

### 3.2 AI FDE vs Local SDK 역할 분담
AI FDE 는 Ontology Manager property 삭제 권한 없음 → **조회/비교/진단** 만 가능 + **Transform/Code Repo 생성** 가능. 이 제약이 다음 분업을 만듦:

| 작업 | 실행 주체 |
|---|---|
| Dataset Arrow schema 조회, property 충돌 분석 | AI FDE |
| Foundry Transform 파이프라인 (bim-mesh-uri-transform) 작성 | AI FDE |
| Object Type property 삭제/타입 변경 | 사용자 (UI) |
| 로컬 parquet 수정 (컬럼 리네임, prefix 제거) | Claude Code (여기) |
| Foundry dataset 재업로드 (SDK) | Claude Code (여기) |

### 3.3 Piping 와 Structural 의 비대칭 상태 (왜 구조만 먼저 성공했나)
- Structural 먼저 등록됨 → `_BimObject` 접미사 패턴 으로 interface fulfillment → 타입 충돌 없음 → indexer 통과
- Piping 은 spec 수정 반영 후 등록 → 동일 ID (`mesh_uri`) 에 로컬+interface 충돌 → indexer 실패
- **즉, UI wizard 의 fulfillment 패턴이 세션 간 일관되지 않았음**

### 3.4 아키텍처 전환: 6 specialized → 1 unified
- Cross-type 링크 문제 + 추후 live streaming 확장 요구 가 겹치면서 **6개 specialized OT 대신 단일 BimObject OT + `refined_class` 필터 프로퍼티** 전략 채택
- streaming 시나리오 에서 단일 스트림 → 단일 dataset → 단일 OT 로 flow 가 자연스러워짐
- 중복 없음 (UNION 을 별도 OT 에 통합하는 것이 아니라 단일 OT 의 backing dataset 이 UNION 결과 자체)
- 기존 BimPiping OT (62 properties) 는 **piping-domain 전용 view** 로 보존 (sp3d_pipeline, design_pressure_kpa 등 piping-only)

---

## 4. 해결방안

### 4.1 단계별 조치 순서

| # | 조치 | 실행 주체 | 결과 |
|---|---|---|---|
| 1 | 로컬 6개 parquet `sp3d_sp3d_moniker` → `sp3d_moniker` rename | Claude Code | 6 files renamed |
| 2 | 로컬 `piping.parquet` `mesh/` prefix 제거 | Claude Code | 2,909 values cleaned |
| 3 | `bim_piping` dataset 재생성 + 재업로드 (신규 RID) | Claude Code (SDK) | 3,062 × 219 업로드 완료 |
| 4 | BimPiping Object Type 삭제 후 재등록 (UI) | 사용자 | 219 auto-import → 156 삭제 → 63 유지 |
| 5 | 누락된 `sp3d_construction_type` 수동 추가 (오타 컬럼 `sp3d_constuction_type` 만 잡혔었음) | 사용자 | 63/63 |
| 6 | mesh_uri → Media Reference (property type) + bim_mesh Media Set (capabilities) | 사용자 | 타입 설정 완료 |
| 7 | `Data Format Violation` 3,062 전수 발생 → `mesh/` prefix 제거 → 재업로드 | Claude Code | 1차 indexer pass |
| 8 | AI FDE 가 Foundry Code Repo `bim-mesh-uri-transform` 작성 (Phase A 나머지 5개) | AI FDE | 6 `*_with_media_ref` dataset 생성 (매칭률 60~91%) |
| 9 | BimPiping 3,062 objects 로딩 완료 ✅ | — | — |
| 10 | Equipment/Electrical/HVAC/Other 개별 등록 시도 → **아키텍처 전환 결정** | 사용자 + AI FDE | — |
| 11 | AI FDE 가 6개 `_with_media_ref` dataset UNION → `bim_objects` (12,009 rows) 생성 | AI FDE | — |
| 12 | 사용자가 BimObject 통합 Object Type 등록 | 사용자 | 12,009 objects |
| 13 | BimPipelines Object Type 등록 (147 objects) | 사용자 | — |
| 14 | 4 Link Type 생성 (adjacentTo Join table / hasParent+inGroup FK / belongsToPipeline FK) | 사용자 | — |

### 4.2 확정된 아키텍처 결정 (PROJECT-JOURNAL.md §4 업데이트 대상)

**D-AIFDE-21 — 단일 BimObject Object Type + `refined_class` 필터 (vs 6 specialized)**

- **맥락**: Phase 3 Link Type 생성 단계에서 `adjacentTo` 가 6개 OT 간 교차이어서 concrete Object Type 쌍으로 선언 불가능. 추가로 live streaming 확장 요구 확인됨.
- **결정**: 6개 `_with_media_ref` dataset 을 UNION 해 단일 `bim_objects` dataset → 단일 `BimObject` Object Type. `refined_class` String property 로 타입 구분 (Piping/Structure/Equipment/Electrical/HVAC/Other).
- **근거**:
  1. Self-link 하나로 cross-type adjacency 110,173 edges 커버
  2. Live streaming 단일 소스 시나리오와 자연스럽게 맞물림
  3. Object 중복 없음 (UNION 을 중복으로 두지 않고 단일 OT 의 backing 으로 채택)
  4. Power BI / Workshop 에서 refined_class 로 필터링 가능
- **Trade-off**: 기존 BimPiping OT (62 properties 의 piping-only 속성 포함) 는 보존. 정밀 도메인 쿼리는 BimPiping, cross-domain 그래프 탐색은 BimObject. 즉 **2-view 병행**.

**D-AIFDE-22 — Media Reference 변환 을 Foundry Transform 으로 수행 (vs SDK 재업로드 sole)**

- **맥락**: `mesh_uri` 컬럼을 Media Reference struct 로 변환할 때 SDK `write_pandas` 는 struct 직렬화 path 신뢰 불확실 (M5 와 유사한 리스크). Foundry Transform 은 Spark 으로 `struct<mediaSetRid, mediaSetViewRid, mediaItemRid>` 생성 보장.
- **결정**: Code Repo `bim-mesh-uri-transform` + `list_media_items_by_path_with_media_ref` API 사용 → `*_with_media_ref` 6개 dataset 생성.
- **근거**: M5 finding (palantir-sdk timestamp → DATE 버그) 의 연장선. Struct 타입은 SDK 보다 Spark 경로가 안전.

### 4.3 발견된 기술 부채 (미해결)
- **Media Reference 매칭률 60~91%**: Media Set 에 해당 GLB 가 없는 경우 null 처리됨. Object 존재 자체에는 문제 없으나 3D viewer 에서 일부 부재. 향후 GLB 추가 업로드 + Transform 재빌드로 해소 가능.
- **BimStructural OT 미업그레이드**: working 상태 보존 위해 mesh_uri=String 그대로. Phase 4 이후 3D viewer 요구 발생 시 동일 파이프라인 재적용.
- **exporter 계획 A vs B 모순**: `src/bimkg/ingest/exporters/foundry.py:23-34` 의 docstring 을 "spec 63" 기준으로 재작성 + column filter 구현 필요 (후속 PR).

---

## 5. 결과

### 5.1 온톨로지 최종 상태 — ✅ **데이터 기본 세팅 완료**

| 분류 | 개수 | 상태 |
|---|---:|---|
| Object Type (통합) | 2 | **BimObject** (12,009, cross-type 뷰), **BimPipelines** (147, aggregate) |
| Object Type (세분화 — 병행 보존) | 6 | BimPiping (3,062), BimStructural (4,840), BimEquipment (770), BimElectrical (1,053), BimHvac (125), BimOther (2,159) |
| Object Type (pending, 후속 30분) | 1 | **BimPipeRun** (378) — dataset 업로드됨, OT 등록 + `belongsToPipeline` (piperun→pipeline) link 만 남음 |
| Link Type | 4 | adjacentTo (110,173), hasParent (12,008), inGroup (12,009), belongsToPipeline (BimObject→BimPipelines, 2,926) |
| Interfaces | 3 | BimObject, HasSP3DMetadata, HasPressureTemp |
| Media Set | 1 | bim_mesh (8,219 GLB) |

### 5.2 검증 결과
- Indexer `EntityTypesNotInitialized` → `Initialized` 전이 확인 (전 Object Type)
- BimObject 12,009 objects 조회 성공
- Link Type 4개 전수 edge count 예상값 일치
- **2-view 전략 확정**: 통합 BimObject (cross-type 그래프 탐색) + 6 specialized OT (도메인별 정밀 쿼리) 병행 운영
- **종합 인사이트 쿼리 성공**: 품질/물리/설계/인접/계층/파이프라인/재료 8개 카테고리 리포트 — [`docs/analysis/bim-kg-insights-20260417.md`](../analysis/bim-kg-insights-20260417.md)
  - 데이터 가치 확인: P-10147 (10,467 kPa 고압 핫라인), Foundation (221 인접 · 620톤 물리 허브), Other 59% 품질 이슈 (M3 parent box 연장), 87,553 overlap 관계 (clash 검출 input)

### 5.3 다음 단계 (데이터 기본 세팅 이후)

**마지막 마무리 작업** (30분 예상):
- [ ] BimPipeRun Object Type 등록 (PK: piperun_id, 26 properties)
- [ ] BimPipeRun → BimPipelines FK link 생성 (pipeline_name) — "Belongs To Pipeline" / reverse "Pipe Runs"

**문서 정리 follow-up**:
- [ ] `docs/plan/ontology-registration-cheatsheet.md` 업데이트 (새 RIDs + BimObject 통합 전략 반영)
- [ ] `src/bimkg/ingest/exporters/foundry.py` docstring + column filter 수정 (계획 A→B 통합)
- [ ] `scripts/rename_double_prefix_column.py` git 추적 대상으로 이동 or 삭제 결정

**Phase 4 진입 준비** (애플리케이션/운영 단계):
- [ ] Workshop 대시보드 구축 — BimObject refined_class 필터 + 링크 네비게이션 + 3D Media Reference 뷰어
- [ ] Object Explorer / Vertex 그래프 시각화 (adjacentTo, hasParent)
- [ ] Schedule 자동 재빌드 (bim_objects UNION 데이터셋 변경 시)
- [ ] Streaming 전환 설계 (단일 스트림 → 단일 dataset → 즉시 인덱싱 흐름, D-AIFDE-21 에서 예비됨)
