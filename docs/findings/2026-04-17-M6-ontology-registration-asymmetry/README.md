# 2026-04-17 — M6 — Ontology Registration 비대칭 실패 (5개 중첩 원인)

**발견 일자**: 2026-04-17
**해결 일자**: 2026-04-17 (same-day)
**Severity**: 🟠 MAJOR
**Status**: ✅ **Resolved** (BimObject 단일 통합 OT 로 아키텍처 전환; BimPiping 재등록 + 6개 `_with_media_ref` dataset 생성)
**Discovered by**: BimPiping Object Type 등록 시 Funnel `EntityTypesNotInitialized` 영구 고정
**Affects**: Foundry 온톨로지 등록 전수 (6 Object Type + 2 Aggregate + 4 Link Type)

---

## 1. Finding

**한 문장**: BimStructural 은 성공하고 BimPiping 은 실패하는 비대칭 상태였는데, 조사 결과 **단일 원인이 아니라 5개 중첩 문제** 가 순차적으로 드러남 — null Arrow dtype, property auto-import bloat, 이중 prefix 컬럼명, meshUri interface ID collision, Media Reference path 불일치.

핵심 숫자:
- BimPiping: 3,062 objects **100%** schema resolution 실패
- BimStructural: 4,840 objects 정상 작동 (비교군)
- Dataset 당 auto-import property: 170+ (spec 은 63/59/53/51/50/45)
- Media Reference 1차 시도 시 3,062 rows **전수** `Data Format Violation`

---

## 2. Evidence

### 2.1 Reproducible audit

```bash
.venv/bin/python docs/findings/2026-04-17-M6-ontology-registration-asymmetry/audit.py
```

audit 스크립트는 6개 Object Type parquet 을 스캔하여 다음을 보고:
1. `null` Arrow dtype 컬럼 개수 + spec 교집합
2. `sp3d_sp3d_moniker` vs `sp3d_moniker` 존재 여부
3. `mesh_uri` sample 값의 `mesh/` prefix 여부
4. `ingested_at_utc` Arrow type (M5 regression 감지)

### 2.2 Data artifacts

`evidence/` 하위:
- `cross_dataset_schema_diff.csv` — 6개 dataset 간 Arrow dtype 불일치 45 컬럼 (string vs null)
- `piping_vs_structural_nullmap_spec_intersection.csv` — 각 type 별 null-typed 매핑 컬럼 수 (piping=1, structural=4, hvac=1, other=0)
- `mesh_uri_path_format_samples.csv` — `mesh/UUID.glb` vs `UUID.glb` 포맷 샘플

### 2.3 Key finding: cross-type asymmetry

```
type           rows  cols  null_cols  spec_cols  null∩spec  problem columns
---------------------------------------------------------------------------------
🔴 piping       3062   219         64         63          1  ['nav_item_source_file_name']
🔴 structural   4840   219         51         57          4  ['nav_item_source_file_name',
                                                             'sp3d_description',
                                                             'sp3d_material_type',
                                                             'sp3d_reporting_type']
🔴 equipment     770   219         63         53          2  ['nav_item_source_file_name', 'sp3d_area']
🔴 electrical   1053   219         54         51          2  ['nav_item_source_file_name', 'sp3d_short_code']
🔴 hvac          125   219         67         50          1  ['nav_item_source_file_name']
✅ other        2159   219         25         45          0  []
```

**이 숫자가 null-dtype 이론을 기각한 근거**: structural 은 null 매핑이 piping 의 4배인데 정상 작동 → null dtype 단독 원인 아님.

---

## 3. Analysis

### 3.1 Root causes (5개 중첩)

#### R1 — Parquet `null` Arrow dtype leak
`palantir-sdk` 의 `write_pandas` 가 전부 NaN 인 object 컬럼을 Arrow `null` 타입으로 직렬화. M5 (DATE 직렬화) 와 같은 write_pandas path 의 또 다른 degenerate case.

- **증상**: 219 컬럼 중 25~67 개가 Arrow null → Foundry resolver 가 코얼스 규칙에서 fallback
- **결론**: **원인 아님** — Foundry 가 실제로는 null → string 으로 암묵적 승격 처리 (structural 에서 작동)

#### R2 — "Create Object Type" auto-import bloat
Foundry UI 마법사가 backing dataset 의 전체 219 컬럼을 자동 매핑 → spec (63 for piping) 대비 ~107개 과다 property.

- **증상**: Property list 바이트수 증가 + 불필요한 null 매핑 다수
- **결론**: **부분 원인** — bloat 자체는 동작 가능 (structural 도 같은 상태였음) 이지만, 다음의 R4/R5 를 확률적으로 증폭시킴

#### R3 — 컬럼명 이중 prefix (`sp3d_sp3d_moniker`)
DXTnavis XLSX loader 가 `sp3d_` prefix 를 이중 부여. Foundry camelCase 자동 매핑 (`sp3dMoniker` → `sp3d_moniker` 기대) 과 불일치.

- **증상**: Interface `HasSP3DMetadata.sp3dMoniker` → source column 수동 매핑 필요
- **결론**: **영향 있음** — 수동 매핑 단계가 추가되며 실수 여지 증가

#### R4 — meshUri Interface Property ID collision (결정적)
같은 `BimObject` interface 를 서로 다른 fulfillment 패턴으로 구현.

- BimStructural: `mesh_uri_BimObject` (별도 property ID, Media Reference) + 로컬 `mesh_uri` (string) 공존 → 타입 충돌 없음
- BimPiping: `mesh_uri` 단일 ID 가 로컬 (string) + interface (Media Reference) 겸용 → **타입 충돌 → indexer resolve 실패**

- **증상**: `EntityTypesNotInitialized` 가 Save 반복해도 전이 안 됨
- **결론**: **결정적 원인** — Funnel 이 schema 에서 타입 불일치 감지 시 초기화 거부

#### R5 — Media Reference path 불일치 (최종 blocker)
```
Media Set 파일 실제 경로: UUID.glb              (scripts/upload_glb_to_foundry_mediaset.py:111 기준)
Dataset mesh_uri 컬럼 값:  mesh/UUID.glb         (exporter 가 출력한 값)
```

- **증상**: R4 해결 후 indexer 초기화는 시작 → 3,062 rows 전수 `Data Format Violation: Misconfigured media reference data sources`
- **결론**: **최종 blocker** — path 포맷 매칭 실패로 Foundry 가 Media Reference 검증 거부

### 3.2 Impact
- BimPiping 등록 지연 (수 시간)
- 나머지 5개 Object Type 과 4개 Link Type 이 모두 연쇄 지연됨 (BimPiping 해결 후에야 진행)
- 문서상 "63개 spec" 가이드가 실제 UI 결과와 불일치 하다는 괴리 노출

### 3.3 Related known issues
- [M5 — palantir-sdk Timestamp → DATE 직렬화](../2026-04-16-M5-timestamp-schema-mismatch/README.md): 동일 write_pandas path 의 자매 버그 (timestamp 대신 null dtype)
- `docs/plan/ontology-registration-cheatsheet.md:52-77` — auto-import 후 spec 으로 정리하는 워크플로우가 문서에 없었음
- `src/bimkg/ingest/exporters/foundry.py:23-34` — "all 216 columns, let Foundry decide" 원설계가 cheatsheet 의 "spec 63" 과 모순

---

## 4. Resolution

### 4.1 Options considered

| 옵션 | 접근 | 장점 | 단점 | 채택 |
|---|---|---|---|:-:|
| A | Property 137개 수동 삭제 | OT RID 보존 | ~45분 클릭 작업, 재발 가능 | ❌ |
| B | BimPiping 삭제 + 재등록 + Select cols | 클린 스타트 | RID 변경 | ✅ piping 만 |
| C | Dataset exporter 수정 + 전수 재빌드 | 뿌리 해결 | 시간 소요 | 📋 Deferred |
| D | 6 OT 전수 유지 + adjacentTo 를 BimObject Interface 로 선언 | 기존 구조 유지 | Interface 기반 Link Type 선언 가능성 불확실 | ❌ |
| E | **6 OT UNION → 단일 BimObject OT + refined_class 필터** | **Streaming-ready, cross-type link 자동 커버** | 기존 6개 specialized OT 삭제 고민 | ✅ **최종 채택** |

### 4.2 Selected approach — 아키텍처 전환 (Option E)

6개 specialized Object Type 구조 대신 **단일 통합 BimObject OT** + `refined_class` String property 로 타입 구분.

**구현**:
1. AI FDE 가 Foundry Code Repo `bim-mesh-uri-transform` 작성 → 6개 `_with_media_ref` dataset 생성 (Media Reference struct + `mesh/` prefix 제거)
2. AI FDE 가 UNION 파이프라인 작성 → `bim_objects` dataset (12,009 rows, 218 columns)
3. 사용자가 Ontology Manager 에서 BimObject OT 등록
4. 사용자가 4 Link Type 전부 self-link / FK 로 BimObject 위에 생성
5. 기존 BimPiping OT 는 piping-domain view 로 병행 보존 (62 properties)

### 4.3 Action items

- [x] 로컬 6개 parquet `sp3d_sp3d_moniker` → `sp3d_moniker` rename
- [x] 로컬 `piping.parquet` `mesh/` prefix 제거
- [x] `bim_piping` 새 RID 로 재업로드 (SDK path)
- [x] BimPiping Object Type 재등록 + 63 properties 정리 + Media Reference 설정
- [x] `bim-mesh-uri-transform` Foundry Code Repo (AI FDE)
- [x] `bim_objects` UNION dataset (AI FDE)
- [x] BimObject Object Type 등록 (사용자)
- [x] BimPipelines Object Type 등록 (사용자)
- [x] 4 Link Type 전수 생성 (사용자)
- [ ] `docs/plan/ontology-registration-cheatsheet.md` 업데이트 (BimObject 통합 전략 반영)
- [ ] `src/bimkg/ingest/exporters/foundry.py` docstring + column filter 정비 (후속 PR)
- [ ] `scripts/rename_double_prefix_column.py` git 추적 결정 (커밋 or 삭제)
- [ ] DXTnavis Issue: XLSX loader `sp3d_` 이중 prefix 업스트림 수정 요청

### 4.4 Resolution evidence

- 세션 task log: [`../../tasklog/phase-2-3-ontology-registration-20260417.md`](../../tasklog/phase-2-3-ontology-registration-20260417.md)
- Foundry 등록 완료: BimObject 12,009 / BimPipelines 147 / BimPiping 3,062 / 4 Link Types 전수 edge count 일치

---

## 5. References

- **Source files**:
  - `src/bimkg/ingest/exporters/foundry.py` (exporter 원설계)
  - `src/bimkg/ingest/exporters/foundry_upload.py` (SDK 재업로드 경로)
  - `scripts/upload_glb_to_foundry_mediaset.py:111` (Media Set 경로 포맷)
  - `scripts/rename_double_prefix_column.py` (컬럼 리네임 스크립트)
- **Related docs**:
  - `docs/plan/ontology-registration-cheatsheet.md` (Phase 1/2 등록 가이드)
  - `docs/findings/2026-04-16-M5-timestamp-schema-mismatch/` (자매 finding)
- **Foundry resources** (신규):
  - `bim_piping` (재생성): `ri.foundry.main.dataset.19583834-1d30-471a-a25b-1b92f682fcb8`
  - `bim_objects` (UNION): `ri.foundry.main.dataset.7d5c883e-a60e-46d2-acbe-ea741447b129`
- **External**: DXTnavis XLSX loader `sp3d_` 이중 prefix 는 업스트림 이슈 대상
