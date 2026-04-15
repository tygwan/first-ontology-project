# AI FDE Session — Phase 2 Ontology Modeling

**Date**: 2026-04-15
**Phase**: 2 — Ontology Structure Design
**Duration**: ~90 min across 3 AI FDE response rounds
**AI FDE Config**:
- Model: (unspecified by user)
- Skills: Ontology Modeler, Data Engineer (inferred from output quality)
- Docs attached: Same as Phase 1 + Phase 1 session log
- Tools enabled: Dataset Reader + Schema inspection

**Goal**: 6 Object Types + 1 new (BimPipeline) + Interface/Mixins + 4 Link Types 스펙 확정. Foundry UI 등록 준비 상태 달성.

---

## 1. Session Context

### Prior state (Phase 1 마감 상태)
- 5개 설계 결정 (D-AIFDE-1~5) 완료
- `foundry-dataset-profiles-2026-04-15.md` 작성됨
- AI FDE 가 "No clarifying questions — ready to proceed" 상태

### Starting questions going in
- Property tier 분류 (core/extended/hidden) 구체화
- Interface 공통 property 확정
- Mixin 개수 결정 (HasPressureTemp 외 추가 필요성?)
- BimPipeline 상세 스펙
- Link Type cardinality / symmetric flag

---

## 2. Key Questions Raised by AI FDE

### Round 1 — AI FDE 의 BimPiping v1 스펙 + 4 questions

AI FDE 가 **4-tier property classification** 으로 BimPiping 63 properties 제시:
- Tier 1 Interface: 32
- Tier 2 Piping-specific: 19
- Tier 3 Niche: 5
- Tier 4 Navisworks meta: 7
- Excluded: ~137

**4가지 질문**:
- Q1: 63-property selection 동의?
- Q2: 나머지 5 타입 스펙 작성?
- Q3: BimPipeline 지금 스펙?
- Q4: 등록 준비 완료?

### Round 2 — AI FDE 의 revisions + 5 delta specs + Interface

**4가지 revision request 적용** + 5 타입 delta spec + Interface/Mixin 스펙 + 4 Link Type 스펙.

**Critical finding**:
> Equipment has 0% fill for design_pressure_kpa and design_temperature_c.
> HasPressureTemp NOT applicable to Equipment.

우리 Phase 1 추측 (Piping + Equipment) 가 데이터 검증으로 **기각**.

### Round 3 — Final Review Doc 발행

AI FDE 가 9-section Notepad 발행:
- Scope/Context, Object Types, Interfaces, Link Types, Excluded, Data Quality, Checklist, Roadmap, Object Sets
- Blocked on 2 items: `bim_pipelines` 업로드, `ingested_at_utc` cast

---

## 3. Decisions Made (continuing from Phase 1)

### D-AIFDE-6: BimPipeRun을 first-class Object Type 으로 승격

**Decision**: Phase 2 에 `BimPipeRun` Object Type 포함 (Phase 1 의 D-AIFDE-2 "defer" 결정 뒤집음).

**Context change**: 사용자가 **"pipeline, piperun 단위는 플랜트 산업에서 쓰는 연결단위"** 라고 확언. 공사 관리가 PipeRun 단위로 이뤄진다고 지적 → Phase 3 operational layer 와 직접 연결되는 엔티티임이 명확해짐.

**Alternatives considered**:
- Phase 1 원래 결정 유지 (PipeRun 을 link property 로만) — **기각** (공사 관리 단위와 불일치)
- Phase 3 으로 연기 — **기각** (나중에 Phase 2 재작업 비용 > 지금 15분 추가 비용)

**Rationale**:
- `Pipeline` (147) : `PipeRun` (378) : `Piping` (3,062) = 1 : 2.6 : 20.8
- 공사 관리 (Phase 3 방향 G) 의 주 단위는 **PipeRun** — 1급 엔티티 필요
- 이미 `bim_piping.sp3d_pipe_run` 데이터 보유, 집계만 하면 됨

**Implementation**:
- Composite primary key: `piperun_id = {pipeline_name}::{pipe_run_name}`
- Backing: 신규 `bim_piperuns` dataset (378 rows × 26 cols)
- Aggregation: `scripts/build_pipeline_aggregates.py`
- Foundry RID: `ri.foundry.main.dataset.4c65a69a-75f3-4ece-ba52-c266d597f3a2`

**Trade-offs accepted**:
- 추가 Object Type 1개 등록 + Link Type 1개 (`belongsToPipeRun`) 추가
- 약 15분 추가 시간

**Cross-references**:
- Phase 1 session log D-AIFDE-2 (수정됨)
- `foundry-next-steps-roadmap.md` 방향 G

---

### D-AIFDE-7: `ingested_at_utc` String → Timestamp cast

**Decision**: 모든 8개 backing dataset 에서 `ingested_at_utc` 를 `datetime64[ns, UTC]` 로 cast.

**Alternatives considered**:
- String 그대로 두기 — Foundry 에서 시계열 쿼리 불가능
- Timestamp + String 양쪽 보존 — 중복

**Rationale**:
- Foundry 의 시계열 쿼리 (e.g., "최근 7일 재처리된 객체") 가능해짐
- Cast 비용: 각 dataset re-upload 한 번 (~5분 total)
- 0 NaT 발생 (모든 값 ISO 8601 유효)

**Execution**:
- `scripts/cast_timestamp_columns.py` 작성
- 6 기존 Object Type dataset re-upload
- 2 신규 (bim_pipelines, bim_piperuns) 는 생성 시점부터 datetime

**Cross-references**:
- AI FDE Final Review §6 Data Quality Notes

---

### D-AIFDE-8: Equipment HasPressureTemp 제외 (Piping-only mixin)

**Decision**: `HasPressureTemp` mixin 은 BimPiping 에만 구현. Equipment/Structural/Electrical/HVAC/Other 는 구현 안 함.

**Evidence driving decision**:
```
design_pressure_kpa fill by type:
  Piping     77%
  Equipment   0%  ⚠️  <- 예상 밖
  Structural  0%
  Electrical  0%
  HVAC        0%
  Other       0%

design_temperature_c: same pattern
```

**Phase 1 에서 우리가 가정한 것** (`Piping + Equipment 에 HasPressureTemp`) 이 데이터 검증으로 **부정**됨.

**Rationale**:
- Mixin 은 "구현 타입 전부 fill > 50%" 여야 의미 있음
- Equipment 0% 는 upstream DXTnavis export 의 누락 — 스키마 결정이 아닌 데이터 이슈
- Mixin 을 "모든 물리 객체에 적용 가능" 으로 억지 일반화하면 오해 소지

**Mitigation (Phase 3+ 에)**:
- DXTnavis Equipment 메타데이터 export 확장 요청 → 향후 DXTnavis PR 후보
- 데이터가 생기면 Equipment 에 mixin 구현 추가

**Cross-references**:
- Phase 1 session log D-AIFDE-5 (update: HasPressureTemp scope 축소)
- AI FDE Round 2 "⚠️ IMPORTANT FINDING" 섹션

---

### D-AIFDE-9: `nav_item_guid` 보존 (M1 forensic trail)

**Decision**: `nav_item_guid` 를 Tier 4 (Navisworks metadata) 에 유지. 제거하지 않음.

**Key discovery by AI FDE**:
```
SELECT COUNT(*) FROM bim_piping
WHERE object_id != nav_item_guid
-- result: 136
```

이 136 이 **M1 의 `classification_confidence = LIKELY_BUG` 행 수 (136)와 정확히 일치**.

**Interpretation**: M1 finding 해결 시 `object_id` 가 재할당됐지만 `nav_item_guid` 는 **원본 Navisworks GUID 를 보존**. 즉:
- `object_id` = 현재 (post-M1) 정상 식별자
- `nav_item_guid` = Navisworks 원본 (pre-M1) 식별자
- 두 값의 차이 = M1 의 감사 증거

**Trade-offs accepted**:
- Property 1개 추가로 storage 증가 (미미)

**Rationale**:
- 감사 가능성 (audit trail) 은 데이터 품질 투명성의 핵심
- 추후 "이 객체가 언제 reclassify 됐는지" 추적 가능
- M1 finding 이 실제로 데이터에 남긴 흔적을 Ontology 가 노출

**Cross-references**:
- M1 finding: `docs/findings/2026-04-12-M1-piping-misclassification/`

---

### D-AIFDE-10: Phase 3 Operational Layer 로드맵 등재

**Decision**: 공사 관리 / 운영 데이터 를 **Phase 3 방향 G** 로 공식 등재. 현재 구현하지 않음.

**Scope documented in roadmap**:
- 3 신규 Object Types: BimTask, BimCrew, BimSchedule
- 2 신규 Link Types: hasTask, assignedToCrew
- Actions: MarkTaskComplete, UpdateTaskProgress, AssignCrew, ReportBlockingIssue
- Functions: computeRemainingDays, forecastCompletion, crewUtilization, earnedValueAnalysis
- Workshop 앱: "Construction Dashboard"
- 외부 data 연결: P6 / MS Project export

**Why defer (not do now)**:
- Phase 2 범위 = 이미 있는 데이터의 Ontology 모델링
- 공사 관리 데이터는 **신규 생성 필요** (schedule, cost, crew 데이터 부재)
- 섞으면 register gate 무한 연기

**Why document now (not later)**:
- 사용자가 "향후 진행할 것이니" 로드맵 등재 확정
- Phase 2 에서 **BimPipeRun 승격** 결정이 Phase 3 의 전제가 됨 — 지금 기록해야 맥락 보존
- Phase 3 외부 data 수집 계획을 미리 고민할 시간 확보

**Cross-references**:
- `docs/plan/foundry-next-steps-roadmap.md` 방향 G (신규 섹션)

---

### D-AIFDE-11: Mixin 최소주의 (HasLinearExtent, HasMaterialProperties 불채택)

**Decision**: Phase 1 에서 고민했던 추가 mixin 들 기각. Interface 1개 + Mixin 2개로 확정.

**Rejected mixins**:
- `HasLinearExtent` (width_m, depth_m, length_m) — Structural/Electrical/HVAC 에 있음
  - 기각: semantics 가 타입마다 다름 (structural beam 의 width ≠ cable tray 의 width)
- `HasMaterialProperties` (sp3d_material, sp3d_material_name, sp3d_material_type) — Structural 44% fill
  - 기각: Structural 외 모든 타입 0% fill → mixin 불성립

**Final mixin inventory**:
| Mixin | Properties | Implementers | Fill % |
|---|---|---|---|
| BimObject (Interface) | 34 | 모든 6 types | core 100%, flags 100% |
| HasSP3DMetadata | 3 | 모든 6 types | 38%–96% varies |
| HasPressureTemp | 2 | Piping only | 77% |

**Rationale**:
- Mixin 인플레이션은 설계 오염 → 최소주의
- 필요하면 Phase 3+ 에 추가 가능

---

### D-AIFDE-12: 용어 분리 원칙 (BIM pipeline ≠ Foundry Pipeline Builder)

**Decision**: AI FDE 와 모든 세션에서 다음 용어를 엄격히 분리하여 사용한다.

| 용어 | 의미 | 범주 |
|---|---|---|
| **Pipeline** (BIM 도메인) | 플랜트 배관 시스템 (예: "P-10147 crude oil feed") — 공정 연결 단위 | Ontology Object Type (`BimPipeline`) |
| **PipeRun** (BIM 도메인) | 배관의 시공/설치 세부 구간 — 작업 할당 단위 | Ontology Object Type (`BimPipeRun`) |
| **Pipeline Builder** (Foundry 도구) | 파생 dataset 생성 + lineage 추적하는 ETL 도구 | Foundry tool |

**Trigger**: AI FDE 가 Round 3 Final Review Doc 이후 "Pipeline Builder" 이라는 Foundry 용어를 사용하기 시작. 우리 BIM `Pipeline` Object Type 과 혼동 가능성 대두.

**Rationale**:
- 도메인 용어와 도구 용어가 같은 단어를 쓰면 문맥 추론 실패 시 심각한 오해
- AI FDE 가 `BimPipeline` Object Type 을 "Pipeline Builder 로 만든 dataset" 으로 잘못 참조할 수 있음
- 지금 명시적으로 분리해두면 이후 모든 세션 일관성 확보

**Implementation**:
- AI FDE 에 보낸 답변 서두에 용어 표 명시
- 이후 모든 session log 에 이 원칙 적용

**Cross-references**:
- AI FDE Round 3 (Final Review Doc) → Round 4 (3 discrepancies) 대응 답변

---

### D-AIFDE-13: Raw Data 불변 + Pipeline Builder 의무

**Decision**: 업로드된 raw dataset 은 수정 금지. 향후 모든 derivation 은 Foundry Pipeline Builder 로 수행한다.

**Scope 명시**:
- **Raw (수정 금지)**: bim_piping, bim_structural, bim_equipment, bim_electrical,
  bim_hvac, bim_other, bim_adjacent_to, bim_has_parent,
  bim_belongs_to_pipeline, bim_in_group
- **Our derivations (iteration 가능)**: bim_pipelines, bim_piperuns
  (Ontology 등록 전까지)
- **향후 모든 변경**: Pipeline Builder

**Trigger**: 사용자의 거버넌스 지시.
> "원본이 손상되지 않도록 Pipeline Builder 를 활용하도록 한다"

**Rationale**:
- Foundry 가 lineage 자동 추적 → 재현성
- 원본 audit 보존 → 데이터 품질 투명성
- Source refresh 시 재실행 가능 → 운영 비용 절감
- raw 와 derivation 명확히 구분 → 팀 협업 시 혼선 방지

**⚠️ Sunk Cost Acknowledgment**:
이 원칙 수립 **전에** 이미 `scripts/cast_timestamp_columns.py` 가
raw 6 datasets 에 timestamp cast 를 적용함 (D-AIFDE-7). 되돌리지 않되,
향후 이와 같은 raw 수정은 금지. 원칙 수립을 **사건 후** 한 것은 정직한
기록으로 남김.

**Trade-offs accepted**:
- Pipeline Builder 학습 시간 필요 (사용자 아직 미숙)
- 간단한 변경도 UI 단계를 거쳐야 함 (ad-hoc Python 대비 느림)

**Revisit condition**:
- Pipeline Builder 가 특정 변환에서 한계를 보이면 (예: 복잡한 KPI 계산)
  Foundry Functions + Ontology edit 로 우회 검토

**Cross-references**:
- D-AIFDE-7 (timestamp cast — 원칙 수립 전 작업)
- D-AIFDE-14 (3 discrepancy 처리에서 이 원칙 적용)

---

### D-AIFDE-14: 3 Discrepancy Triage (AI FDE Round 3 대응)

**Context**: AI FDE 가 Round 3 에서 3가지 데이터 불일치 flag.

| # | 이슈 | 영향 |
|---|---|---|
| ① | `corrosion_risk_score`, `isolation_section_count` KPI 가 bim_pipelines 에 없음 | BimPipeline 29 cols (AI FDE 추측 31 cols) |
| ② | `ingested_at_utc` 가 Date type (Timestamp 기대) | 시계열 precision 손실 |
| ③ | `piperun_id` 가 bim_belongs_to_pipeline 에 없음 | belongsToPipeRun link 등록 불가 |

**Decision (각각)**:

| # | 선택지 | 결정 | 이유 |
|---|---|---|---|
| ① | (a) 재업로드 / (b) Phase 3 Pipeline Builder 조인 | **(b)** | KPI 데이터 아직 Foundry 에 없음. Phase 3 operational layer 와 묶어 처리. |
| ② | (a) 재cast / (b) Date 수용, 필요시 나중 cast | **(b)** | Phase 2 blocker 아님. Timestamp precision 은 Phase 3 operational task 에서 필요할 때 Pipeline Builder cast. |
| ③ | (a) Pipeline Builder 파생 dataset / (b) sp3d_pipe_run 직접 link | **(a)** | D-AIFDE-13 원칙 적용. 원본 수정 없이 composite key 유지. |

**Rationale**:
- Phase 2 등록을 **지연시키지 않음** — 현재 자산으로 기본 Ontology 먼저 완성
- Pipeline Builder 작업은 **등록 직후 cleanup** 으로 스케줄
- KPI / Timestamp 는 **Phase 3 operational layer 착수 시** 필요해지면 처리

**Implementation plan**:

1. **Ontology registration (즉시, AI FDE Round 4)**:
   - 7 Object Types + Interface + 2 Mixins
   - 4 Link Types (belongsToPipeRun 제외)

2. **Post-registration cleanup (24h 이내)**:
   - Pipeline Builder: `bim_belongs_to_pipeline` → `bim_belongs_to_piperun`
     (derived column: `piperun_id = CONCAT(pipeline_name, '::', pipe_run_name)`)
   - `belongsToPipeRun` Link Type 등록

3. **Phase 3 operational layer 착수 시**:
   - Pipeline Builder: KPI dataset 조인 → `bim_pipelines_enriched`
   - Pipeline Builder: Timestamp cast (필요 확인 후)
   - BimPipeline backing 을 enriched view 로 전환

**Cross-references**:
- AI FDE Round 3 "Three Data Discrepancies to Flag" 섹션
- `docs/plan/foundry-next-steps-roadmap.md` 방향 G (Phase 3)

---

## 4. Discoveries / Surprises

### 🆕 Discovery 1: `nav_item_guid` 이 M1 감사 증거
- 136 mismatches = 정확히 M1 LIKELY_BUG count
- 우리가 M1 finding 때 인지하지 못한 보존 구조
- **Action**: docs/findings/2026-04-12-M1-piping-misclassification/ 에 cross-reference 추가 후보

### 🆕 Discovery 2: Equipment Pressure/Temp 0%
- Phase 1 에서 "Piping + Equipment 가 HasPressureTemp 구현" 으로 가정
- 실제 Equipment 는 **전혀 없음**
- **Implication**: Equipment 객체 분석 시 pressure/temp KPI 불가능 — upstream 해결 필요

### 🆕 Discovery 3: `valve_count = 0` in bim_pipelines
- 147 pipelines 모두 `valve_count = 0` (display_name 에 "valve" 없음)
- 616 flanges, 0 valves (비현실적 — 실제 플랜트는 반드시 valve 포함)
- **가설**:
  - (a) Valve 가 `bim_equipment` 에 분류됐을 가능성
  - (b) Valve mesh 가 `gap_fallback.fbx` 에 supplemented 로 들어있고 명명이 다름
- **Action**: M5 후보는 아님 (명명 규칙 이슈), Workshop 설계 시 Valve 쿼리 방식 고민 필요

### 🆕 Discovery 4: OK_LINE_MESH 와 SKIP_IS_HIDDEN verdict
- 우리가 기존에 catalog 안 한 `verdict` 값 2개:
  - `OK_LINE_MESH`: 선 전용 geometry (8 objects in bim_other)
  - `SKIP_IS_HIDDEN`: 의도적으로 숨긴 객체 (7 objects in bim_other)
- **Implication**: `is_hidden` flag 가 "forward-compatibility 만" 이 아니라 실제 **사용 중**
- **Action**: M5 후보 아님, 데이터 완전성 증빙

### 🆕 Discovery 5: 플랜트 규모의 "단순성"
- 378 piperuns / 147 pipelines = avg 2.6 piperuns/pipeline
- 예상 500–1000 보다 낮음
- 이 플랜트는 **비교적 단순한 배관 구조** (training dataset 성격)
- **Portfolio 맥락**: demo 시 "educational scale" 로 프레이밍

---

## 5. Action Items

### Completed this session
- [x] BimPiping 63 property spec 확정 (revisions 4개 적용)
- [x] 5 delta specs (Structural 59 / Equipment 55 / Electrical 53 / HVAC 52 / Other 45)
- [x] Interface BimObject (34 props) 확정
- [x] Mixins: HasSP3DMetadata (3), HasPressureTemp (Piping-only, 2)
- [x] 4 Link Type specs (adjacentTo, hasParent, belongsToPipeline, inGroup)
- [x] BimPipeline spec (22 + bonus 7 props, 147 rows)
- [x] bim_pipelines dataset 생성 + 업로드
- [x] bim_piperuns dataset 생성 + 업로드 (bonus)
- [x] ingested_at_utc cast 적용 (8 datasets)
- [x] Phase 3 방향 G 로드맵 등재
- [x] AI FDE Final Review Doc 9-section 발행 확인

### Completed in Round 4 (AI FDE side)
- [x] BimPipeRun Object Type spec (26 properties)
- [x] belongsToPipeRun Link Type spec (flagged: needs piperun_id)
- [x] pipeRunInPipeline Link Type spec (new, BimPipeRun → BimPipeline)
- [x] 3 data discrepancies flagged by AI FDE
- [x] Final Review Doc 발행 (9 sections)

### Pending AI FDE Round 5 (사용자 답변 전달 완료, 분석 중)
- [ ] D12-14 수용 확인 (용어 분리, Pipeline Builder, discrepancy triage)
- [ ] Ontology editing mode 전환
- [ ] 등록 실행 (Interface → Mixins → 7 Object Types → 4 Link Types)
- [ ] belongsToPipeRun 은 등록 후 Pipeline Builder 작업 대기

### Pending user action
- [ ] Phase 2 session log (이 파일) 커밋
- [ ] AI FDE Round 4 응답 수신 → Phase 2 conclusion

### Phase 3 pre-work (when ready)
- [ ] 외부 schedule 데이터 소스 결정 (P6 / MS Project / Excel / 수기)
- [ ] BimTask / BimCrew / BimSchedule 세부 스펙 (AI FDE Phase 3 session)
- [ ] DXTnavis PR 2건 제출 (M4 + Equipment pressure/temp)

---

## 6. Prompt/Response Artifacts

### 가장 임팩트 컸던 AI FDE 응답
> "136 mismatches between object_id and nav_item_guid — exactly matching the 136 classification_confidence = LIKELY_BUG objects from M1."

이 한 문장이 **감사 가능성 설계 결정** 을 만들어냄. 우리가 M1 archive 할 때 이 관계를 주목하지 않았음.

### 가장 위험했던 AI FDE 추정의 자기 교정
Phase 1 에서 우리가 "Piping + Equipment 에 HasPressureTemp" 라고 가정했는데,
Round 2 에서 AI FDE 가 데이터 profile 로 재검증하여 "Equipment 는 0%, HasPressureTemp NOT applicable" 로 수정.
**Lesson**: Phase 1 의 intent-level 가정은 Phase 2 데이터 검증으로 반드시 재확인.

### Round 2 AI FDE 의 응답 구조 (매우 명확)
- Part A: Revisions applied (근거 + before/after)
- Part B: 5 delta specs (중복 제거 / class-specific 만)
- Part C: BimPipeline spec
- Part D: Interface specifications
- Part E: Link Type specifications

이 포맷을 **Phase 2 템플릿으로 재활용** 가능.

---

## 7. Meta-reflection

### What went well
- AI FDE 의 **데이터-기반 검증** — 우리의 Phase 1 가정 2건 뒤집음 (HasPressureTemp scope, nav_item_guid 의미)
- `bim_pipelines` + `bim_piperuns` 병렬 생성으로 register gate 빨리 통과
- Phase 3 방향 G 를 **지금 로드맵에 등재** → 사용자의 운영 관점을 잃지 않고 Phase 2 범위 유지

### What went poorly
- Phase 1 에서 Equipment HasPressureTemp 가정을 데이터 확인 없이 했음 (Phase 2 에서 뒤집힘)
- Valve 문제는 Phase 2 초반에 눈치챌 수 있었는데 aggregate 결과 나온 후에야 발견
- **Pipeline Builder 거버넌스 원칙을 사건 후 수립** (D-AIFDE-13) — `cast_timestamp_columns.py`
  가 raw 를 먼저 수정한 뒤에야 원칙 명시. 향후는 선행 수립 지향.

### Next session improvements
- **Phase 3 session prompt** 에 "Equipment pressure/temp 0% 를 인지하고 workaround 제시" 포함
- **Phase 3 session** 에서 valve 쿼리 전략 (equipment cross-join) 논의
- 외부 schedule data 준비가 되면 Phase 3 session 착수
- Foundry Ontology Manager 로 이동한 뒤에도 session log 유지 (등록 단계도 기록 대상)

---

## 8. Files Produced/Modified This Session

### Created
- `scripts/build_pipeline_aggregates.py` — BimPipeline + BimPipeRun 집계 스크립트
- `scripts/cast_timestamp_columns.py` — `ingested_at_utc` timestamp cast 스크립트
- `data/ontology/2026-04-12/bim_pipelines.parquet` (147 × 29)
- `data/ontology/2026-04-12/bim_piperuns.parquet` (378 × 26)

### Modified
- `docs/plan/foundry-next-steps-roadmap.md` — 방향 G (Operational Layer) 섹션 추가
- Foundry datasets: 6 existing + 2 new re-uploaded with timestamp cast

### Session artifacts (AI FDE side)
- Final Review Notepad (9 sections) — AI FDE 에서 발행됨, 참조용
- Checklist 상태: Phase 2 완료 직전 (Round 4 대기)
