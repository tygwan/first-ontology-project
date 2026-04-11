# Phase 2 — Planning Checkpoint (Paused pending DXTnavis PR)

**일자**: 2026-04-12
**담당 Task**: #18
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| Markdown | `docs/PROJECT-JOURNAL.md` | §1 한눈에 보기 업데이트 + §1 Decisions 테이블에 D10, D11 추가 + §2 Timeline 에 Phase 2 planning checkpoint 추가 + §4 에 D10, D11 full records 추가 + §5 External Dependencies DXTnavis blocking 상태 기록 + §6 Open Questions 재구조화 (Q1/Q3 resolved, Q2 업데이트, Q4 신규) |
| Markdown | `docs/tasklog/phase-2-planning-checkpoint.md` | 이 문서 |

**구현 코드 변경 없음** — Phase 2 는 실제 구현 시작 전 planning 단계이며, 데이터가 변경될 예정이라 구현 시작 자체가 deferral 됨.

### 작업 내용 요약

Phase 2 (OWL 온톨로지) 를 시작하기 위해 R8 (Human-AI collaboration) 원칙에 따라 사용자와 structural 질문 8 개를 논의:
- Q1 top-level taxonomy 구조
- Q2 클래스 계층 깊이
- Q3 Piping LIKELY_BUG 처리
- Q4 RDF serialization 포맷
- Q5 Pipeline/PipeRun 표현 방식
- Q6 ABox 파일 분할
- Q7 Property datatype
- Q8 spatial_relationships.ttl 관계

각 질문에 대해 trade-off 분석 (Option A/B/C 포함) 을 제시하고 추천안을 전달.

사용자 결정:
- **Q1**: Option A (sibling `BIMObject ‖ AnalysisArtifact`) 채택 → **D10**
- **Q2~Q8**: DXTnavis 측에서 원천 수정 PR 을 작성할 예정이므로, 데이터가 변경될 때까지 대기 → **D11**

---

## 2. 문제

**발생한 기술적 문제 없음**. 이 작업은 planning 단계이므로 코드/테스트 변경이 없었음.

**의사결정 차원의 문제**: Phase 2 의 7 개 구조적 질문이 입력 데이터의 최종 형태에 의존하는데, DXTnavis 원천 데이터가 M1 finding 으로 인해 수정 예정 상태임. 이 상태에서 Phase 2 를 구현하면:
- Piping 4,014 → ~2,926 변화 시 모든 ABox triples 재생성 필요
- 클래스 count 기반 아키텍처 결정 (예: 파일 분할 단위) 이 무효화
- PipingComponent 개체의 특정 rdf:type 선언이 재분류됨

→ 즉, **정확성과 일정의 trade-off** 를 판단해야 하는 상황.

---

## 3. 분석

### Phase 2 각 질문의 데이터 의존도

| 질문 | 데이터 의존 | 변동 예상 |
|------|:-:|----------|
| Q1 top-level taxonomy | ❌ | 없음 (구조 결정) |
| Q2 계층 깊이 | ⚠️ 간접 | Eqp Type 0 커버리지가 증가할 수 있음 |
| Q3 LIKELY_BUG 처리 | ✅ 직접 | **LIKELY_BUG 자체가 사라질 수 있음** |
| Q4 serialization 포맷 | ⚠️ | 데이터 크기 변화 |
| Q5 Pipeline individual | ✅ 직접 | 147 → ~157 로 증가 가능 |
| Q6 ABox 파일 분할 | ✅ 직접 | 각 파일 크기 재계산 |
| Q7 Property datatype | ❌ | 없음 |
| Q8 spatial_relationships.ttl | ⚠️ | DXTnavis 수정에 포함될 수 있음 |

Q1, Q7 은 데이터 독립적이므로 지금 결정 가능. 나머지는 대기가 적절.

### 왜 Phase 2a (TBox) 만이라도 진행하지 않는가

TBox (schema) 는 개념상 데이터 독립적입니다. 클래스/속성 정의만 포함하고 실제 객체는 없음. 따라서 DXTnavis fix 가 있어도 TBox 자체는 거의 변하지 않음.

**그럼에도 완전 일시 중단을 선택한 이유**:
1. **흐름의 일관성**: 2a 만 진행하면 통합 테스트가 분리됨. 한 번에 깔끔하게 가는 것이 후방 이해 비용 감소
2. **데이터 기반 세부 사항**: TBox 라도 일부 property range (예: `xsd:double` vs `xsd:integer`) 는 데이터를 보고 결정하는 것이 안전
3. **재개 시 동기부여**: 중단과 재개의 경계가 명확해야 "언제 시작하지?" 라는 질문에 답하기 쉬움
4. **짧은 대기 가정**: DXTnavis PR 이 수일 내 제출 가능하다면 2a 만 진행하는 이점은 작음

### dev-standards R8 원칙 적용

이 planning checkpoint 자체가 R8 (Human-AI collaboration) 의 실제 적용 사례임:
- AI (Claude) 가 8 개 질문에 대해 각각 3 옵션 + pros/cons + 추천 제시
- 사용자가 명시적으로 승인/거부 (Q1 승인, Q2~Q8 defer)
- 결정 과정이 R4 (Decision Records) 형식으로 기록 (D10, D11)

이는 dev-standards 의 examples/first-ontology-project.md 에서 설명한 R8 적용 패턴과 정확히 일치.

---

## 4. 해결방안

### D10 — Phase 2 top-level taxonomy 확정

```
BIMEntity
├── BIMObject (sibling)
│   ├── PhysicalObject
│   │   ├── PipingComponent, StructuralMember, Equipment,
│   │   │   Support, ElectricalComponent, HvacComponent,
│   │   │   UncategorizedObject
│   └── Container
│       └── HierarchyNode
└── AnalysisArtifact (sibling)
    └── AnalysisVolume
        ├── InsulationVolume
        ├── FireproofingVolume (future)
        └── AcousticVolume (future)
```

Phase 1a 심화 논의 (§4.3) 에서 이미 권고되었고, SHACL positive rule 작성 + 미래 분석 아티팩트 확장 이유로 선택.

### D11 — Phase 2 Q2~Q8 구현 deferral

**재개 조건** (D11 에 10-item 체크리스트):
1. DXTnavis Issue #2 PR 제출
2. PR merge + 새 DXTnavis 버전 release
3. 사용자가 Navisworks 에서 XLSX 재 export
4. 새 스냅샷 파일 복사
5. `SNAPSHOT` 상수 업데이트
6. `run_phase_1a()` 재실행
7. `classification_confidence` 분포 확인 (모두 HIGH 기대)
8. Phase 1d exporter 재실행
9. 전체 테스트 통과 확인 (expected count 갱신 가능성)
10. Phase 2 Q2~Q8 재평가

### PROJECT-JOURNAL.md 업데이트

1. **§1 한눈에 보기**: Phase 2 Paused 상태 표시 + 재개 조건 요약
2. **§1 Decisions 테이블**: D10, D11 행 추가
3. **§2 Timeline**: 2026-04-12 Phase 2 planning checkpoint entry
4. **§4 Decisions 상세**: D10 full record + D11 full record (맥락/결정/근거/대안/영향/관련/재개 조건)
5. **§5 External Dependencies**: DXTnavis 섹션에 "Phase 2 blocking" 명시
6. **§6 Open Questions**:
   - Q1, Q3 → ✅ Resolved 표시 (strikethrough)
   - Q2 → 상태 업데이트 (PR 작성 예정)
   - Q4 신규 → Phase 2 Q2~Q8 재개 후 재평가 대기

---

## 5. 결과

✅ **PROJECT-JOURNAL.md 업데이트 완료**
- §1 Quick Problem Index: Decisions 테이블 10 → 12 행 (D10, D11 추가)
- §2 Timeline: 2026-04-12 부분에 Phase 2 planning checkpoint 라인 추가
- §4 Decisions: D1~D11 full records (D10, D11 신규 작성)
- §5 External Dependencies: DXTnavis 섹션에 Blocking 관계 명시
- §6 Open Questions: Q1/Q3 resolved, Q2 업데이트, Q4 신규

✅ **구조적 결정 기록**
- D10: Phase 2 top-level taxonomy = sibling (`BIMObject ‖ AnalysisArtifact`)
- D11: Phase 2 Q2~Q8 구현 대기 (재개 체크리스트 10 항목 포함)

✅ **테스트 영향 없음** — 210/210 유지 (코드 변경 없음)

✅ **task log 작성** (이 문서)

### 다음 단계

**단기 (DXTnavis PR 대기 중)**:
- 사용자: DXTnavis Issue #2 에 대한 PR 작성
- 병렬 가능 작업:
  - Power BI Desktop 에서 현재 `fact_objects.csv` 로 검증 대시보드 구축
  - dev-standards v0.1.1 미세 개선 (발견되는 typo / 개선 사항)
  - Phase 2 구현 전 준비: OWL 기본 개념 학습, rdflib 튜토리얼, SPARQL 기본

**중기 (PR merge 이후)**:
- D11 §재개 조건 체크리스트 순차 실행
- 새 XLSX 스냅샷으로 Phase 1a/1d 재실행
- Phase 2 Q2~Q8 재평가 + 구현 (Phase 2a/2b/2c 원래 계획대로)

**장기 (Phase 2 완료 이후)**:
- Phase 3 (SHACL 검증 + OWL 추론)
- Phase 4 (Graph Analytics, Phase 2/3 와 병렬 가능)
- Phase 5 (LLM/GraphRAG)
- Phase 6 (FastAPI)
- Phase 7 (Streamlit UI)

### 교훈

**이 checkpoint 가 보여준 것**:
1. "Wait state" 자체도 문서화할 가치가 있음 — "무엇을, 왜 기다리는가" 가 기록되어야 재개 가능
2. 데이터 의존성이 있는 설계 결정은 데이터 품질 확보 후에 하는 것이 이중 작업을 방지
3. Finding (M1) → External issue (DXTnavis #2) → Deferral (D11) → Resume checklist 의 흐름이 연결되어 있음
4. dev-standards R4 + R6 + R8 이 모두 이 한 작업에 적용됨 — 규칙이 서로 보강하는 걸 실제로 경험
