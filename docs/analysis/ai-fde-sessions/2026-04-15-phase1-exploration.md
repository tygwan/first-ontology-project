# AI FDE Session — Phase 1 Exploration

**Date**: 2026-04-15
**Phase**: 1 — Data Exploration (pre-Ontology)
**Duration**: ~30 min (first response round)
**AI FDE Config**:
- Model: (unspecified by user)
- Skills: Data Engineer (inferred)
- Docs attached: Project folder with 11 datasets (AI FDE can directly read)
- Tools enabled: Dataset Reader (confirmed by AI FDE behavior)

**Goal**: 11개 데이터셋을 Ontology 로 모델링하기 전, AI FDE 와 **공유된 이해** 구축. 놓친 설계 질문 발굴.

---

## 1. Session Context

### Prior state
- 11 datasets uploaded to `/Datayoon-09825c/BIM-KG/` (6 Object + 4 Link + 1 Media Set)
- Ontology not yet configured (0 Object Types registered in Datayoon Ontology)
- 4 prior findings resolved (M1–M4), 33 KPIs pre-computed
- `docs/analysis/foundry-dataset-profiles-2026-04-15.md` 존재

### Starting questions going in
- 219 컬럼 중 어느 것을 core/extended/hidden 으로 분류?
- Pipeline (147) 을 Object Type 으로 승격해야 하나?
- Adjacency 110K edges 를 어떻게 모델링?

---

## 2. Key Questions Raised by AI FDE

AI FDE 가 데이터를 분석한 후 Ontology 모델링 전에 결정해야 한다고 제시한 5개 질문. 데이터 스키마만 봐서는 답하기 어려운 **intent-level 질문** 들.

### Q1: One Object Type or Six?

모든 6개 데이터셋이 동일한 ~200 컬럼 스키마를 공유. Ontology 모델링 선택지:

- **(A)** 단일 `BimObject` type — 6개 UNION, `refined_class` 로 필터, Interface 로 공통 shape.
  - 장점: 단순
  - 단점: property list 가 거대해지고 non-piping 타입에서 대부분 sparse
- **(B)** 6개 분리 Object Type (현재 상태 유지)
  - 장점: domain semantics 명확
  - 단점: 모든 Link 가 cross-type reference 를 처리해야 함 (Piping ↔ Structural adjacency)
- **(C)** Hybrid — 단일 `BimObject` + Interface + class별 view/object set
  - 장점: 양쪽 장점 결합

**AI FDE's recommendation**: Option C (단, 다운스트림 앱 intent 확인 후)

---

### Q2: Pipeline 과 Zone 을 first-class Object Type 으로?

`bim_belongs_to_pipeline` 과 `bim_in_group` 은 link-like 하지만 전용 entity table 이 없음. 사용자가 pipeline/zone 으로 검색/필터할 거라면 승격 필요:

- `BimPipeline` (147 objects) 생성?
- `BimZone` / `BimGroup` (3,355 objects) 생성?

**AI FDE's recommendation**: (explicit 안 함, 사용자 intent 필요)

---

### Q3: Ontology 레이어에서 무엇을 필터링할까?

비물리적 객체 카테고리 존재 (container, bbox placeholder, parent box, hidden). `is_parent_box`, `is_container`, `is_bbox_placeholder`, `is_hidden`, `graph_participant` 플래그 존재.

- **(A)** 전부 포함, Workshop 에서 사용자가 필터
- **(B)** dataset/backing layer 에서 제외 (깔끔하지만 hierarchy 손실)

**AI FDE's recommendation**: (명시 안 함)

---

### Q4: Adjacency tier 를 어떻게 노출?

110K adjacency edges, 3 tiers (overlap/touch/neartouch). 모두 Ontology link 로 materialize 하면 interactive app 에 부담 가능.

- **(A)** 단일 link type + `relation_type` property (flexible but dense)
- **(B)** tier 별 분리 link type (overlaps/touches/near)
- **(C)** 'strong' 만 (overlap + touch) Ontology 노출, 'neartouch' 는 dataset 에서만 analytics 용도

**AI FDE's recommendation**: (명시 안 함)

---

### Q5: Target applications / workflows?

Ontology 모델은 use case 를 서빙해야 함. AI FDE 가 제시한 5가지 후보:

1. **3D Viewer** — 객체 brows, click to inspect, adjacency navigate → mesh URI 가 media-backed property 필요
2. **Pipeline Inspector** — pipeline 선택, component 조회, spec 확인 → Pipeline first-class entity 필요
3. **Spatial Analytics** — "1m 이내 고압 배관 근처 장비" → distance filter 포함 adjacency
4. **Construction/Maintenance** — status, material, weight 추적 → SP3D property surface
5. **Zone Analysis** — Louvain zone 별 KPI aggregation → Zone first-class entity 필요

---

## 3. Decisions Made

### D-AIFDE-1: Object Type structure = **B + Interface** (not C)

**Decision**: 6개 분리 Object Type + 공통 Interface `BimObject` (선택적 mixin interfaces).

**Alternatives considered**:
- **Option A (단일 BimObject)**: 219 cols 중 ~50% 가 class 별로 null (예: `design_pressure_kpa` 은 Piping/Equipment 에만 의미, HVAC/Structural 에서 null). UI 가 추악해짐. **기각**.
- **Option C (Hybrid 단일 + Interface + View)**: AI FDE 권장이지만, Foundry 에서 "단일 Object Type + View" 패턴은 복잡도 높음. 6개 이미 disjoint 하게 업로드되어 있어 분리 유지가 자연스러움. **기각**.
- **Option B (6 분리) + Interface**: 도메인 의미 명확 + 공통 쿼리 가능 (interface 로). **채택**.

**Rationale**:
- 12,009 객체 disjoint 검증됨 (dataset profile §1)
- Operators think "piping" vs "equipment", not "BimObject with filter"
- Cross-type Link 은 Foundry 에서 자연스럽게 지원됨
- Interface 로 "모든 BIMObject 중 bbox > X" 같은 쿼리 가능

**Trade-offs accepted**:
- 6개 Object Type 을 각각 UI 에서 등록해야 함 (registration 시간 ~30–60 min)
- Property spec 을 6번 반복해야 함 (Interface 에 위임하면 완화됨)

**Revisit condition**:
- Foundry Workshop 에서 cross-type query 가 Interface 만으로 충분한지 확인
- 만약 부족하면 Object Set view 추가 고려

**Cross-references**:
- `docs/analysis/foundry-dataset-profiles-2026-04-15.md` §1 (disjoint 증명)
- 로드맵 `docs/plan/foundry-next-steps-roadmap.md` 방향 A

---

### D-AIFDE-2: Pipeline = first-class, Group/Zone = defer

**Decision**:
- **Create** `BimPipeline` Object Type (147 entities from DISTINCT `sp3d_pipeline`)
- **Defer** `BimGroup` (3,355 groups, 3,353 이 singleton)
- **Defer** `BimZone` (144 Louvain zones — 아직 업로드 안 됨)

**Alternatives considered**:
- All three as Object Types — 모델링 비용 크고 일부는 데이터 없음 (Zone)
- None as Object Type — pipeline-level 쿼리가 SQL-heavy 가 됨

**Rationale**:
- 147 distinct pipelines 는 "show pipeline X" 쿼리의 빈도가 높음
- 33 KPIs 중 pipeline-level 8개 존재 → `BimPipeline.totalWeight`, `BimPipeline.corrosionRisk` 로 properties 승격 가능
- `BimGroup` 은 분포가 극단 (99.9% singleton) → Object Type 으로 승격 가치 없음
- `BimZone` 은 별도 upload 작업 필요 → 우선순위 낮춤 (Phase 3)

**Trade-offs accepted**:
- Group/Zone 관련 쿼리는 직접 SQL/aggregation 으로 처리해야 함
- Zone 기능 필요해지면 Phase 3 에서 추가 upload + Object Type 등록

**Revisit condition**:
- Zone analysis 가 portfolio demo 에서 필요해지면 → Zone Object Type 추가
- Multi-element Group 의 수가 늘어나면 → Group Object Type 고려

**Cross-references**:
- `src/bimkg/analytics/kpi.py` pipeline-level KPIs
- `docs/findings/2026-04-12-M2-adjacency-tiers/` — 관련 context

---

### D-AIFDE-3: Non-physical filtering = **Option A (include everything)**

**Decision**: 12,009 객체 전부 Ontology 에 포함. 비물리적 필터링은 Object Set 기능으로 해결.

**Alternatives considered**:
- **Option B (dataset layer 에서 제외)**: 깔끔하지만 `bim_has_parent` (12,008 rows) 의 hierarchy 관계가 깨짐. 448 parent_box 는 M3 에서 의도적으로 flag 한 것. **기각**.

**Rationale**:
- M3 finding 에서 `is_parent_box` flag 를 의도적으로 유지했음 (pipeline_fragmentation 분석 때 필요)
- Filtering 을 Ontology layer 에 두면 **irreversible** (되돌리려면 전체 재등록)
- Workshop/OSDK 는 saved Object Set 을 지원 → "Physical Only" 필터를 재사용 가능한 bookmark 로

**Trade-offs accepted**:
- 기본 Object Type 쿼리가 container/placeholder 를 반환할 수 있음 → UI 에서 명시적 필터 필요
- 사용자가 실수로 container 객체를 분석 대상에 포함할 위험

**Mitigation**:
Standard Object Sets 을 Phase 3 에서 생성:
- `PhysicalObjectsOnly`: `is_container=false AND is_parent_box=false AND is_bbox_placeholder=false`
- `GraphParticipants`: `graph_participant=true`
- `FullMeshOnly`: `mesh_quality='full_mesh'`

**Cross-references**:
- `docs/findings/2026-04-13-M3-parent-box-contamination/` (M3 finding)

---

### D-AIFDE-4: Adjacency = **Option A (single link + relation_type property)**

**Decision**: 단일 `adjacentTo` Link Type. `relation_type`, `distance_m`, `overlap_volume_m3`, `tolerance_m`, `is_symmetric` 를 link-level properties 로 보존.

**Alternatives considered**:
- **Option B (tier 별 분리)**: UI 복잡도 3배, 쿼리 3배, UX 이점은 marginal. **기각**.
- **Option C (Strong/Medium 만)**: 이미 M2 에서 3 tier 를 의미 있게 정의했음. weak 제거하면 "all adjacency" 쿼리 불가. **기각**.

**Rationale**:
- 110K edges 는 Foundry 기준 가벼움 (10M+ 프로젝트 사례 존재)
- `relation_type` 으로 clean filter 가능 (`WHERE relation_type='touch'`)
- M2 에서 3 tier 는 **analytics concept** 이지 **schema concept** 이 아님 — 그 철학을 유지

**Trade-offs accepted**:
- 기본 쿼리가 110K edges 를 다 볼 수 있음 → 반드시 filter 권장
- UI에서 "strong only" 단축 버튼을 제공해야 함

**Mitigation**:
- Workshop widget 의 default filter 를 `relation_type IN ('touch', 'overlap')` 로 설정

**Cross-references**:
- `docs/findings/2026-04-12-M2-adjacency-tiers/` (M2 finding)

---

### D-AIFDE-5: Target apps = **전부, 3D + Pipeline 우선**

**Decision**: 5개 use case 전부 범위 안이나 우선순위 명확:

- **Priority 1** (Phase 2 필수):
  - 3D Viewer — `mesh_uri` → Media Reference 필수
  - Pipeline Inspector — `BimPipeline` 필수 (D-AIFDE-2)
- **Priority 2** (Phase 3):
  - Spatial Analytics — distance-filter adjacency 쿼리
  - Construction/Maintenance — SP3D properties surface
- **Priority 3** (Phase 3+):
  - Zone Analysis — Zone Object Type 필요 (D-AIFDE-2 defer)

**Alternatives considered**:
- 모든 5개를 Phase 2 에 집어넣기 — 범위 폭발
- 3D Viewer 하나만 집중 — 포트폴리오 demo scenarios 가 단조로워짐

**Rationale**:
- 3D Viewer 는 portfolio demo 의 "wow factor" 요소
- Pipeline Inspector 는 plant maintenance 도메인의 가장 흔한 workflow
- Zone Analysis 는 advanced analytics 로, 나머지 4개가 먼저 동작하지 않으면 의미 없음

**Cross-references**:
- 로드맵 `docs/plan/foundry-next-steps-roadmap.md` §3 방향 A, B

---

## 4. Discoveries / Surprises

AI FDE 가 새로 지적한 것 중 우리가 놓쳤던 것:

### 🆕 Discovery 1: Pipeline을 데이터셋이 아닌 Object Type으로 승격해야 한다는 관점

우리는 `bim_belongs_to_pipeline` 을 Link Type 으로만 생각했지, `BimPipeline` 자체를 Object Type 으로 만들 생각을 하지 않았음. 이게 핵심 개선점.

→ **Action**: `bim_pipelines` 신규 dataset 생성 필요 (147 rows, aggregated from `bim_piping`)

### 🆕 Discovery 2: Interface 개념의 명시적 활용

우리 로드맵에서 Interface 는 언급만 했지 구체 설계는 아직 없었음. AI FDE 가 Q1 에서 Interface 를 통한 hybrid 접근을 제시 → **Phase 2 설계에 필수 포함**.

### 🆕 Discovery 3: Object Set이라는 Foundry 개념

"filter 를 Ontology 에 두지 말고 Object Set 으로" 라는 제안은 Foundry specific pattern. 재사용 가능한 필터 bookmark 개념.

→ **Action**: Phase 3 에서 `PhysicalObjectsOnly`, `GraphParticipants`, `FullMeshOnly` 생성

### ⚠️ Potential new finding (not M5 yet)

AI FDE가 지적하지 않았지만 데이터를 보면서 확인된 것:
- `bim_structural` 의 `sp3d_system_path` 중 2,397개가 빈 문자열 (`""`)
- Gold 단계에서 null 처리가 일관되지 않을 수 있음
→ 검증 스크립트 필요 시 M5 archive 고려

---

## 5. Action Items

- [x] 5개 결정을 문서화 (이 파일)
- [ ] **사용자**: 답변 초안을 AI FDE 에 전달 (제안된 정본 참고)
- [ ] **사용자**: AI FDE 의 다음 응답 공유
- [ ] **다음 세션 (Phase 2)**:
  - Interface `BimObject` 속성 상세 설계
  - 6 Object Type 각각 YAML 스펙 작성
  - Mixin interfaces (`HasSP3DMetadata`, `HasPressureTemp`) 결정
- [ ] **신규 데이터 작업**:
  - `bim_pipelines` dataset 생성 스크립트 (147 rows aggregation)
  - Foundry 업로드
- [ ] **빈 문자열 일관성 검증 스크립트** (M5 후보)

---

## 6. Prompt/Response Artifacts

### 우리가 AI FDE 에 보낸 context (session 시작)

Phase 1 session script (`docs/plan/ai-fde-session-scripts/01-phase1-exploration.md`) Prompt 1 기반. 11 datasets 구조, 4 prior findings, 33 KPIs, 144 zones 를 명시.

### AI FDE 가 제공한 응답의 품질

- **강점**: Intent-level 질문 (schema 분석만으로는 나올 수 없는 질문) 제기
- **약점**: Q3, Q4 에서 명시적 recommendation 주지 않음 (user 가 결정해야 함)
- **인상적인 부분**: "No clarifying questions from me at this stage" → 데이터 이해는 충분, 사용자 의도만 있으면 된다는 명확한 신호

---

## 7. Meta-reflection

### What went well
- AI FDE 의 5개 질문이 **정확히 설계 결정 지점**을 찍음
- 우리 dataset profile 이 AI FDE 에게 유용한 context 가 된 듯 (어느 컬럼이 sparse 인지 빠르게 파악)
- Pipeline first-class 제안은 우리가 놓쳤던 좋은 발견

### What went poorly
- AI FDE 가 3/5 질문에서 explicit recommendation 안 함 → 사용자가 판단해야 함 (AI 가 autonomy 부족)
- "Option C 가 권장" 이라는 말을 했지만 실제로는 복잡도를 과소평가 (B 가 더 실용적)

### Next session improvements
- Phase 2 prompt 에 "Always give explicit recommendation, even when you're uncertain" 추가
- Interface 설계 시 "mixin 몇 개가 최적인가" 질문을 미리 준비
- `bim_pipelines` dataset 생성을 먼저 완료하고 들어가기 (AI FDE 가 이 entity 를 볼 수 있도록)
