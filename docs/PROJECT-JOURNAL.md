# Project Journal — first-ontology-project

> **목적**: 이 프로젝트에서 **어떤 문제에 부딫혔고, 어떻게 분석하고, 어떻게 해결했는지** 를
> 한 번의 스크롤로 볼 수 있는 단일 포털 문서.
>
> **사용 방법**: 프로젝트 후반에 "그때 내가 마주했던 문제가 뭐였지?" 라는 질문에 답하려면
> 이 문서 하나만 열면 됩니다. 각 항목은 상세 증거가 있는 파일의 링크를 제공합니다.
>
> **자동 규칙**: 새 이슈 발견 시 `docs/findings/` 에 archive 하고 **반드시 이 문서에도 1줄 추가**.
> 새 Phase 완료 시 `docs/tasklog/` 에 기록하고 **반드시 이 문서 Timeline 에 1줄 추가**.

---

## 한눈에 보기

**프로젝트 상태** (2026-04-12 기준):
- Phase 0 ~ 1e: ✅ 완료 (212 테스트 통과 — 2026-04-12 snapshot 재정렬 완료)
- Phase 2: ⏸ **Paused** — Q1 top-level taxonomy 결정 (D10), Q2~Q8 재개 조건 충족 (D11 재개 가능)
- 발견된 데이터 이슈: 🟠 1건 MAJOR (✅ **Fully Resolved**), 알려진 한계 3건
- DXTnavis 원천 PR: 🟢 [PR #3](https://github.com/tygwan/DXTnavis/pull/3) **Open, Mergeable**, **로컬 빌드로 이미 적용됨**
  - ⚠️ Issue #2 에 제안한 `\b` fix 는 **불충분** — Pipe Rack 같은 composite noun 에 매치됨
  - ✅ 실제 fix: `pipe(?!\s+(rack|trench|support|way|bridge|shoe))` 로 negative lookahead
  - ✅ 2026-04-12 snapshot 으로 전면 재정렬 완료 (config/classifier/tests/data)
- **Standards**: dev-standards@0.1.0 (🟢 first consumer / reference implementation)
- 다음 단계: Phase 2 Q2~Q8 재평가 후 재개 (입력 데이터 안정화됨)
- 병행 작업: Power BI 학습 (PBIP commit 전략으로 `dashboards/powerbi/`)

---

## 섹션 지도

1. [**Quick Problem Index**](#1-quick-problem-index) — "무슨 문제가 있었는지" 한 줄씩
2. [**Timeline**](#2-timeline) — 시간 순서로 본 주요 사건
3. [**Findings (상세)**](#3-findings-상세) — 발견된 데이터/설계 이슈
4. [**Decisions**](#4-decisions) — 내린 중요 결정과 근거
5. [**External Dependencies**](#5-external-dependencies) — 외부 repo / 플랫폼 의존
6. [**Open Questions**](#6-open-questions) — 아직 결정 안 된 것들
7. [**Where to find what**](#7-where-to-find-what) — 자료 위치 빠른 참조

---

## 1. Quick Problem Index

### Data quality issues

| ID | Date | Severity | Title | Status | Archive |
|----|------|:-:|-------|--------|---------|
| M1 | 2026-04-12 | 🟠 MAJOR | XLSX substring matching misclassifies 997 Piping objects | ✅ **Fully Resolved** (PR #3 + re-alignment) | [archive](findings/2026-04-12-M1-piping-misclassification/README.md) |
| M2 | 2026-04-12 | 🟡 MINOR | Adjacency 는 AABB 기반 — 3단계 품질 분류 필요 | ✅ Resolved (tier 분류 도입) | [archive](findings/2026-04-12-M2-adjacency-tiers/README.md) |
| M3 | 2026-04-13 | 🟠 MAJOR | Parent box 객체 448개가 adjacency 66% 오염 | 🔄 Fixing (is_parent_box 플래그 + 재분석) | [archive](findings/2026-04-13-M3-parent-box-contamination/README.md) |

### Known limitations (수용 / 연기)

| ID | Description | Impact | Status |
|----|-------------|--------|--------|
| K1 | validation.csv ParentId 불완전 (294/12,009) | 사용 대체 소스 확보로 해결 | ✅ Resolved (AllProperties.csv 사용) |
| K2 | Equipment Eqp Type 0 커버리지 18% (153/851) | Phase 2 에서 Unclassified subclass 필요 | 🔭 Accept |
| K3 | 147 vs 157 Pipeline 차이 | XLSX 의 FindKey 로직 한계 | 📋 Deferred (DXTnavis PR 에 포함) |
| K4 | data/working/ 1.7GB legacy backup 보존 여부 | 삭제 대신 backup/ 로 이동 | ✅ Resolved |

### Design decisions

| ID | Decision | When | Where documented |
|----|----------|------|------------------|
| D0 | Python 단일 저장소 (C# 백엔드 대체) | Phase 0 | `docs/plan/pipeline-implementation-plan.md` |
| D1 | Medallion architecture (Bronze/Silver/Gold/Ontology) | Phase 1a 재조직 | `docs/tasklog/phase-1a-folder-reorg.md` |
| D2 | XLSX 를 source-of-truth 로 사용 | Phase 1a 설계 | `docs/analysis/phase-1a-data-realignment-design.md` §7 |
| D3 | 2-signal consensus 대신 XLSX 직접 수용 | Phase 1a 심화 논의 | 위 §7 |
| D4 | 4-column lineage scheme | Phase 1a | 위 §7 |
| D5 | Container/AnalysisVolume 을 클래스 아닌 플래그로 | Phase 1a 심화 | 위 §4.1 |
| D6 | Foundry Object Type = all-in-one 216 cols | Phase 1d | `docs/tasklog/phase-1d-exports.md` |
| D7 | Link Type = single direction + is_symmetric flag | Phase 1d | 위 |
| D8 | Power BI + Foundry 병행 출력 | Phase 1d | 위 |
| D9 | Finding archive 규칙 (5단계 프로세스) | 2026-04-12 | `memory/feedback_finding_archive.md` |
| D10 | Phase 2 top-level taxonomy = sibling (BIMObject ‖ AnalysisArtifact) | Phase 2 planning | §4 D10 |
| D11 | Phase 2 Q2~Q8 구현 대기 (DXTnavis PR 후 재개) | Phase 2 planning | §4 D11 |

---

## 2. Timeline

```
2026-04-04   프로젝트 생성 (README: Data Storage Policy)
2026-04-07   DXTnavis v1.4.0 스냅샷 추출 (12,009 objects)
2026-04-10   Phase 0 — Project bootstrap (uv, pytest, config.py)        ddac7b4
             Phase 1b — SP3D unit parser (44 tests)                      8bd8b43
             Phase 1a Step 1-3 — XLSX oracle foundation                  cf70da1
             Phase 1a Step 4 — Silver + Gold pipeline                    1721652
             Phase 1a — Reorganize to Medallion architecture             368bd55
             Phase 1d — Power BI + Foundry exports                       eb67b43
             Phase 1 verification kit                                    69373b1
2026-04-12   Finding M1 discovered during deep semantic audit
             Finding archive rule established (memory + docs/findings/)
             M1 archive committed                                        2f330dc
             DXTnavis Issue #2 submitted
             PROJECT-JOURNAL.md created (this document)                  4214e6d
             Phase 1e — classification_confidence layer (M1 local fix)   6a337e0
             dev-standards@0.1.0 published; first consumer linked        b315437
             Phase 2 planning checkpoint                                  02d57e2
             └── D10: top-level taxonomy = sibling (BIMObject ‖ AnalysisArtifact)
             └── D11: Phase 2 Q2~Q8 paused pending DXTnavis PR
             Power BI dashboard mockups (7 pages) generated              3707481
2026-04-11   DXTnavis PR #3 submitted (upstream)
             └── My \b...\b fix was incomplete (composite noun gotcha)
             └── Actual fix uses negative lookahead
             └── Snapshot drift: 2026-04-12 baseline ≠ 2026-04-07
             └── 153 "Pipelines" objects are actually legit fittings
2026-04-12   DXTnavis PR #3 feedback archived in M1 finding              b73102f
             Stray XLSX cleanup + .gitignore patterns                    25aeb45
             Phase 1 re-alignment to 2026-04-12 snapshot                 (pending)
             ├── New raw: Refining_ObjectID_20260412_064240.xlsx
             ├── xlsx_classifier.py: negative-lookahead regex (PR #3 port)
             ├── Oracle test: 12,009/12,009 = 100% (first try)
             ├── Test count re-baselined: 210 → 212 (+2 boundary tests)
             ├── Class redistribution: Piping 4014→3062, Other 697→2159
             └── M1 finding: Resolved locally → Fully Resolved
```

### Test count progression

| Phase | Test count | Cumulative |
|-------|-----------:|-----------:|
| 0 | +3 | 3 |
| 1b | +44 | 47 |
| 1a (config + oracle) | +32 | 79 |
| 1a (clean + loader + sqlite) | +73 | 149 |
| 1d (exporters) | +43 | 192 |
| 1e (confidence layer) | +18 | 210 |
| 1 re-alignment (2026-04-12) | +2 | 212 |

---

## 3. Findings (상세)

### M1. XLSX substring matching misclassifies 997 Piping objects  🟠 MAJOR — ✅ Fully Resolved

**발견 일자**: 2026-04-12
**발견 경위**: Phase 1 완료 후 데이터 품질 감사 (semantic deep dive) 중
**영향 범위**: Phase 1a Gold, Phase 1d PowerBI + Foundry 출력

**요약**: DXTnavis 의 `RefinedXlsxExporter.InferClass` 가 word boundary 없는 substring 매칭 사용.
- `"tee"` 키워드가 `"steel"` 에 매치 (s-**TEE**-l) → 10건
- `"pipe"` 키워드가 `"Pipe Rack"`, `"Pipe Trench"`, `"Pipeline"` 폴더명에 매치 → 770건
- **Piping 4,014 중 997 (24.8%) 가 실제 Structure/Electrical 임**

**증거 자료**:
- 상세 보고서: [`docs/findings/2026-04-12-M1-piping-misclassification/README.md`](findings/2026-04-12-M1-piping-misclassification/README.md)
- 시각화 4종: [figures/01~04](findings/2026-04-12-M1-piping-misclassification/figures/)
- 재현 스크립트: [audit.py](findings/2026-04-12-M1-piping-misclassification/audit.py)
- CSV 증거 5개: [data/](findings/2026-04-12-M1-piping-misclassification/data/)
- DXTnavis PR draft: [dxtnavis-pr-draft.md](findings/2026-04-12-M1-piping-misclassification/dxtnavis-pr-draft.md)

**외부 조치**: [DXTnavis Issue #2](https://github.com/tygwan/DXTnavis/issues/2) → [PR #3](https://github.com/tygwan/DXTnavis/pull/3) open/mergeable.

**Phase 1 (로컬 완화, Phase 1e, `6a337e0`)**: `classification_confidence` + `classification_confidence_reason` 2 컬럼을 Gold / PowerBI fact_objects / Foundry Object Type 전체에 추가.
- Piping 4,014 분해: **HIGH 2,926 / LOW 91 / LIKELY_BUG 997**
- 원인별 reason 세분화 (pipe_rack / pipe_trench / pipeline_folder / steel_tee_substring / unknown)

**Phase 2 (원천 수정 + 재정렬, 2026-04-12)**: DXTnavis PR #3 의 negative-lookahead regex 를 로컬 Python 포팅에 동일 적용하고, PR #3 로 재생성된 2026-04-12 XLSX snapshot 으로 전체 파이프라인 재실행.
- 재정렬 task log: [`docs/tasklog/phase-1-realignment-20260412.md`](tasklog/phase-1-realignment-20260412.md)
- 최종 클래스 분포: Piping 4,014→3,062, Structure 5,926→4,840, Other 697→2,159, Electrical 449→1,053, HVAC 72→125, Equipment 851→770
- Piping 재분해: **HIGH 2,926 / LOW 0 / LIKELY_BUG 136** (unknown 128 + pipe_rack 잔여 8)
- Oracle 테스트: 12,009/12,009 = 100% (첫 시도)
- 테스트: 212/212 passing (210 → 212, +2 boundary tests)

---

## 4. Decisions

### D2 — XLSX 를 source-of-truth 로 사용

**맥락**: Phase 1a 설계 초기에 5개의 구조적 질문 (Container 정의, 재분류 전략, Insulation Volume 처리 등) 을 논의하고 2-signal consensus classifier 를 작성하기로 했었음.

**전환**: `data/raw/dxtnavis/2026-04-07/Refining_ObjectID_20260407_192047.xlsx` 가 이미 DXTnavis 의 `RefinedXlsxExporter` 가 생성한 분류 결과임을 발견.

**결정**: Python 자체 classifier 를 작성하지 않고 XLSX 를 oracle 로 삼음. 재현 가능성을 위해 C# `InferClass` 를 Python 으로 1:1 포팅하여 12,009 건 100% 일치 테스트 유지.

**근거**: 프로젝트 소유자가 DXTnavis 를 신뢰 → oracle 로 사용 시 원천 동기화 비용 0.

**상세**: [`docs/analysis/phase-1a-data-realignment-design.md`](analysis/phase-1a-data-realignment-design.md) §7

**후속 영향**: M1 버그를 Phase 1d 완료 후에야 발견. 만약 자체 classifier 를 작성했다면 regex word boundary 로 처음부터 회피 가능했을 것. 이는 *trade-off* 로 수용.

---

### D1 — Medallion architecture 채택

**맥락**: Phase 1a 중 data/working/ 1.7GB 의 C# 백엔드 legacy 를 어떻게 처리할지 고민. data/processed/ 단일 디렉터리 vs Phase 별 vs Medallion.

**결정**: Palantir Foundry 의 표준 패턴인 Bronze (raw) → Silver (clean) → Gold (enriched) → Ontology 4 계층 구조 적용.

**근거**:
1. 최종 목표가 Palantir Foundry 이므로 Foundry 의 dataset 패턴과 일치시키면 migration 비용 0
2. 각 계층의 책임이 명확 (Bronze = 변경 없음, Silver = 타입 정규화, Gold = 비즈니스 로직, Ontology = Object/Link Types)
3. 다중 스냅샷 확장 용이 (`data/clean/2026-04-07/`, `data/clean/2026-05-01/` 등)

**상세**: [`docs/tasklog/phase-1a-folder-reorg.md`](tasklog/phase-1a-folder-reorg.md)

---

### D8 — Power BI + Foundry 병행 출력

**맥락**: Phase 1d 에서 출력 포맷 결정. Power BI 만? Foundry 만? 둘 다?

**결정**: 둘 다 생성.

**근거**:
1. 사용자가 Foundry 초심자 → 개발 중 Power BI Desktop 이 빠른 시각 검증 도구 역할
2. 같은 Gold DataFrame 에서 CSV/Parquet 으로 내보내는 비용 차이 거의 0
3. Phase 2 온톨로지 완성 전까지 "숫자만 보고 품질 판단" 하는 리스크 회피
4. 장기 유지 여부는 Phase 2 이후 재평가

**상세**: [`docs/tasklog/phase-1d-exports.md`](tasklog/phase-1d-exports.md)

---

### D10 — Phase 2 top-level taxonomy = sibling 구조

**맥락**: Phase 2 OWL 온톨로지 설계를 위해 top-level 클래스 계층을 결정해야 함. 세 가지 옵션이 논의됨:
- Option A: `BIMObject` 와 `AnalysisArtifact` 를 sibling 으로 분리
- Option B: 단일 트리 — `BIMObject` 아래 모든 클래스
- Option C: 평탄 구조 — 중간 추상 클래스 없음

이전 논의 참조: `docs/analysis/phase-1a-data-realignment-design.md` §4.3 에서 이미 sibling 구조를 권고했으나 최종 결정은 Phase 2 시점으로 연기.

**결정**: **Option A (sibling 구조)** 를 채택.

```
BIMEntity
├── BIMObject
│   ├── PhysicalObject
│   │   ├── PipingComponent
│   │   ├── StructuralMember
│   │   ├── Equipment
│   │   ├── Support
│   │   ├── ElectricalComponent
│   │   ├── HvacComponent
│   │   └── UncategorizedObject
│   └── Container
│       └── HierarchyNode
└── AnalysisArtifact
    └── AnalysisVolume
        ├── InsulationVolume
        ├── FireproofingVolume (미래)
        └── AcousticVolume (미래)
```

**근거**:
1. AnalysisVolume 은 의미론적으로 PhysicalObject 가 아님 — 엔지니어링 분석 아티팩트
2. SHACL 규칙 (Phase 3) 을 positive form 으로 작성 가능 ("PhysicalObject 는 adjacency 에 참여 가능")
3. 미래의 다른 분석 아티팩트 (Clash, StressModel 등) 확장이 자연스러움
4. Phase 1a §4.3 심화 논의의 결론과 일치

**대안 검토**:
- Option B (단일 트리): SHACL 규칙이 negative form 필요 ("AnalysisVolume 은 adjacency 참여 불가"), 복잡도 증가
- Option C (평탄): 서브클래스 추론 이점 상실, SPARQL 쿼리에서 중간 abstraction 활용 불가

**영향**:
- `src/bimkg/ontology/schema.py` 구현 시 이 구조 사용
- Phase 3 SHACL 규칙은 positive 제약으로 작성 가능
- 미래 분석 아티팩트 추가 시 스키마 변경 없이 확장

**관련**: D11 (Phase 2 나머지 논의 연기), Phase 1a §4.3

---

### D11 — Phase 2 Q2~Q8 구현 대기 (DXTnavis PR 후 재개)

**맥락**: Phase 2 planning session 에서 8 개의 구조적 질문을 논의. Q1 은 결정되었으나 (D10), Q2~Q8 은 입력 데이터의 최종 형태에 의존하는 항목들이다.

현재 상황:
- M1 finding 이 XLSX 분류기에서 ~997 건의 false positive Piping 을 발견
- DXTnavis 측에서 원천 수정 PR 을 작성 예정 (Issue #2)
- PR 이 merge 되고 XLSX 가 재생성되면 클래스 분포가 크게 변함:
  - Piping 4,014 → ~2,926 (HIGH 만 남음)
  - Structure 5,926 → ~7,000 (misclassified 흡수)
  - Electrical 449 → ~510
- 따라서 현재 데이터로 ABox 를 생성하면 DXTnavis fix 후 재작업 필요

의존하는 질문들:
- Q2 클래스 계층 깊이 — 데이터 통계에 따라 선택
- Q3 LIKELY_BUG 처리 — DXTnavis 수정 후 LIKELY_BUG 자체가 사라질 수 있음
- Q4 serialization 포맷 — 데이터 크기에 따라 결정
- Q5 Pipeline/PipeRun 표현 — 147 vs 157 pipeline 차이가 해결되어야 결정 가능
- Q6 ABox 파일 분할 — 최종 데이터 크기에 따라
- Q7 Property datatype — 영향 작음
- Q8 spatial_relationships.ttl 관계 — DXTnavis 수정에 포함될 수 있음

**결정**: Q1 (D10) 이후 Phase 2 를 **일시 중단** 한다. Phase 2a (TBox), 2b (ABox), 2c (integration) 모두 DXTnavis Issue #2 가 해결되고 새 XLSX 스냅샷을 확보할 때까지 대기.

**근거**:
1. **정확성 > 일정**: 변경될 데이터 위에 구축하면 이중 작업
2. **Phase 1e confidence column 이 임시 가교**: downstream 필요는 충족됨
3. **D10 은 데이터 독립적**: top-level 구조는 데이터 변경과 무관하므로 결정 유지
4. **Phase 2 의 가치는 데이터가 온전할 때 최대**: 지금 구현해도 곧 폐기

**대안 검토**:
- Option A: 현재 데이터로 그대로 진행 → 이중 작업, 신뢰 저하
- Option B: 완전 일시 중단 ← **선택**
- Option C: Phase 2a (TBox 만) 진행 후 2b/2c 대기
  - TBox 는 사실 데이터 독립적이므로 가능하긴 함
  - 하지만 2a 만 분리하면 통합 흐름이 끊김 → 한 번에 깔끔하게 가기 위해 deferral

**재개 조건 (resume checklist)**:
- [ ] DXTnavis maintainer 가 Issue #2 에 대한 PR 제출
- [ ] PR merge + 새 DXTnavis 버전 release
- [ ] 사용자가 Navisworks 에서 XLSX 재 export 하여 새 스냅샷 획득
- [ ] `data/raw/dxtnavis/<new-snapshot>/` 에 신규 파일 복사
- [ ] `bimkg.config.SNAPSHOT` 상수 업데이트 (또는 새 스냅샷 디렉터리 지원)
- [ ] `run_phase_1a()` 재실행으로 Gold 재생성
- [ ] `classification_confidence` 분포 확인 — 모든 Piping 이 HIGH 가 되는지 검증
- [ ] Phase 1d exporter 재실행으로 PowerBI/Foundry 산출물 갱신
- [ ] 192+ 테스트 전체 통과 확인 (기대 count 업데이트 필요할 수 있음)
- [ ] Phase 2 구조적 Q2~Q8 재평가 (새 데이터 기준으로)

**영향**:
- Phase 2 시작 시점이 외부 의존성에 의해 결정됨 (open-ended)
- Phase 3 (SHACL), Phase 4 (Analytics), Phase 5 (LLM), Phase 6 (API), Phase 7 (UI) 모두 cascaded delay
- 대기 기간 동안 사용자가 할 수 있는 가치 있는 작업: Power BI 대시보드 구축, dev-standards 개선, 문서화

**관련**:
- D10 (유일하게 결정된 Q1)
- DXTnavis Issue #2
- M1 finding
- Phase 1e confidence layer (로컬 임시 가교)

---

## 5. External Dependencies

### DXTnavis (C# .NET 8 BIM data extractor)

**역할**: 플랜트 BIM 모델을 Navisworks 에서 추출하여 CSV/XLSX 로 export.

**저장소**: https://github.com/tygwan/DXTnavis (사용자 소유)

**이 프로젝트에 제공하는 데이터**:
- `AllProperties_*.csv` — 원본 SP3D 속성 136 컬럼
- `Refining_ObjectID_*.xlsx` — 정제된 피벗 + 5 개 summary 시트 ← **primary source**
- `adjacency.csv` — 110,173 producer 공간 관계
- `geometry.csv` — BBox, centroid, mesh 메타
- `validation.csv` — 메시 품질, verdict, GroupId
- `connected_groups.csv` — 3,355 연결 그룹

**의존성 상태**:
- 현재 **2026-04-12 스냅샷** 활성 (2026-04-07 은 historical baseline 으로 보존)
- ✅ M1 (Issue #2) → 🟢 [PR #3](https://github.com/tygwan/DXTnavis/pull/3) 의 regex fix **로컬 빌드에 포팅 완료**
- **PR #3 의 중요 발견** (여전히 유효):
  - Issue #2 에 제안된 `\b` fix 는 **불충분** (Pipe Rack 같은 composite noun 에서 실패)
  - 실제 fix 는 negative lookahead 사용: `pipe(?!\s+(rack|trench|...))`
  - **Snapshot drift**: 2026-04-12 baseline 의 class 분포가 2026-04-07 과 다름 (원천 SP3D 모델 변경 추정)
- ✅ **Phase 2 재개 unblock** — D11 의 재개 체크리스트 전부 충족됨
- 🟡 Data extraction wishlist (Issue #2 Part 2): 별도 follow-up PR 예정
- ⏳ Upstream merge (user action): PR #3 아직 open → merge 후 DXTnavis release 받으면 "내가 만든 로컬 Python port" 와 완전히 동기화됨

**연락 채널**: GitHub Issues/PRs on tygwan/DXTnavis

**Blocking 관계**:
- ~~DXTnavis PR #3 → Phase 2 전체 (2a/2b/2c) 대기~~ → ✅ **Unblocked** (regex 로컬 적용 + 새 snapshot 활성)
- Phase 2 Q2~Q8 재평가만 남음 (입력 데이터 안정화됨)

**대기 기간 가치 활동** (재개 가능, but Phase 2 바로 진입 가능):
- Power BI Desktop 학습 (PBIP commit 전략)
- dev-standards 개선

---

### Palantir Foundry

**역할**: 최종 데이터 플랫폼. Ontology Object Types + Link Types + Workshop 앱.

**이 프로젝트의 사용 계획**:
- Developer Tier (무료) 사용
- 별도의 신규 프로젝트 (기존 Ontology 와 연동 없음)
- Object Type 전략은 데이터 확인 후 결정

**현재 상태**: Phase 1d 가 Foundry-ready Parquet 출력 생성 완료.
실제 import 는 사용자가 수행 예정.

**Foundry 관련 이슈**: 없음 (2026-04-12 기준)

---

## 6. Open Questions

### ~~Q1. M1 해결 전 Phase 2 시작?~~ ✅ Resolved

**해결**: Phase 1e 먼저 실행하기로 결정. 완료됨 (6a337e0). 자세한 내용은 D11 참조.

### ~~Q2. DXTnavis Issue #2 응답 대기 시간?~~ ✅ Resolved

**해결** (2026-04-12): PR #3 의 regex fix 를 Python 포트에 직접 적용하고 2026-04-12 snapshot 으로 재정렬 완료. Upstream merge 는 여전히 pending 이지만 local build 로 unblock 됨. 상세: [`docs/tasklog/phase-1-realignment-20260412.md`](tasklog/phase-1-realignment-20260412.md).

### ~~Q3. Phase 2 OWL 온톨로지 스키마 top-level 구조?~~ ✅ Resolved

**해결**: Sibling 구조 (`BIMObject ‖ AnalysisArtifact`) 채택. D10 참조.

### Q4. Phase 2 Q2~Q8 재개 후 구조적 결정

**질문**: 2026-04-12 snapshot 재정렬 완료 후, 새 데이터를 바탕으로 Phase 2 의 남은 7 개 구조적 질문을 재평가해야 함:
- Q2 클래스 계층 깊이
- Q3 Piping LIKELY_BUG 처리 (PR #3 후 997 → 136 로 크게 감소, 대부분 "unknown" reason)
- Q4 RDF serialization 포맷
- Q5 Pipeline/PipeRun/Level individual 표현
- Q6 ABox 파일 분할
- Q7 Property datatype 전략
- Q8 spatial_relationships.ttl 관계

**상태**: ✅ **Unblocked** — D11 재개 체크리스트 전부 충족. 사용자 판단으로 Phase 2 진입 가능.

**실제 변화** (2026-04-07 → 2026-04-12):
- Piping 4,014 → **3,062** (-952, 오분류 제거)
- Structure 5,926 → **4,840** (-1,086, 일부가 Electrical/HVAC/Other 로)
- Other 697 → **2,159** (+1,462, Pipe Rack/Trench 가 여기로)
- Electrical 449 → **1,053** (+604)
- classification_confidence 분포: Piping HIGH 2,926 / LOW 0 / LIKELY_BUG 136
  - LIKELY_BUG 잔여 136 은 대부분 "unknown" reason — **컬럼 유지 가치 있음**

---

## 7. Where to find what

### 빠른 참조 테이블

| 찾고 싶은 것 | 위치 |
|------------|------|
| 전체 프로젝트 개요 | [`README.md`](../README.md) |
| **데이터 논리 체인** | [`docs/analysis/methodology-data-logic.md`](analysis/methodology-data-logic.md) |
| Phase 구현 계획 | [`docs/plan/pipeline-implementation-plan.md`](plan/pipeline-implementation-plan.md) |
| Phase 1a 설계 논의 | [`docs/analysis/phase-1a-data-realignment-design.md`](analysis/phase-1a-data-realignment-design.md) |
| XLSX classifier 로직 분석 | [`docs/analysis/refined-xlsx-exporter-logic.md`](analysis/refined-xlsx-exporter-logic.md) |
| Phase 1 검증 가이드 | [`docs/analysis/phase-1-verification-guide.md`](analysis/phase-1-verification-guide.md) |
| 완료된 Phase 별 기록 | [`docs/tasklog/`](tasklog/) |
| 발견된 이슈 아카이브 | [`docs/findings/`](findings/) |
| **EDA + CM 노트북** | [`notebooks/`](../notebooks/) (GitHub 에서 시각화 렌더링) |
| DXTnavis 원천 데이터 명세 | [`docs/reference/DATA-SPECIFICATION.md`](reference/DATA-SPECIFICATION.md) |
| 이전 backend 분석 (legacy) | [`docs/reference/dxtnavis-2026-04-07-*.md`](reference/) |

### Code 위치

| 모듈 | 역할 |
|------|------|
| `src/bimkg/config.py` | 경로 상수, expected counts |
| `src/bimkg/ingest/unit_parser.py` | SP3D 문자열 → SI 단위 |
| `src/bimkg/ingest/xlsx_classifier.py` | C# InferClass Python 포트 (oracle) |
| `src/bimkg/ingest/xlsx_loader.py` | XLSX 로드 + snake_case 정규화 |
| `src/bimkg/ingest/clean.py` | Silver + Gold 빌더 |
| `src/bimkg/ingest/sqlite_writer.py` | Parquet + SQLite 출력 + run_phase_1a() |
| `src/bimkg/ingest/exporters/powerbi.py` | 10 CSV star schema |
| `src/bimkg/ingest/exporters/foundry.py` | 6 Object + 4 Link Type parquet |

### Data 위치

| 레이어 | 위치 | 포맷 |
|--------|------|------|
| Bronze (raw, **active**) | `data/raw/dxtnavis/2026-04-12/` | CSV, XLSX, JSON (읽기 전용) |
| Bronze (historical) | `data/raw/dxtnavis/2026-04-07/` | 보존 (비교/감사용) |
| Silver (clean) | `data/clean/2026-04-12/` | Parquet |
| Gold (enriched) | `data/enriched/2026-04-12/` | Parquet + SQLite |
| PowerBI | `data/powerbi/2026-04-12/` | CSV |
| Ontology | `data/ontology/2026-04-12/{object_types,link_types,owl}/` | Parquet / TTL |
| Backup (legacy) | `data/backup/dxtnavis-csharp-20260411/` | 읽기 전용 |

### 검증 / 실행 스크립트

| 파일 | 역할 |
|------|------|
| `scripts/verify_phase1.py` | Phase 1 전체 스냅샷 1회 출력 |
| `docs/findings/*/audit.py` | 각 finding 의 재현 스크립트 |
| `docs/findings/*/make_figures.py` | 각 finding 의 시각화 생성 |

---

## 8. 이 문서 업데이트 규칙

1. **새 finding 발견 시**: `docs/findings/` 아카이브 생성 + 위 §1 "Quick Problem Index" + §3 "Findings 상세" 에 1줄/1섹션 추가
2. **새 Phase 완료 시**: `docs/tasklog/` 기록 + 위 §2 "Timeline" 에 1줄 추가
3. **중요 결정 시**: 위 §4 "Decisions" 에 1섹션 추가 (원인 / 결정 / 근거 / 영향)
4. **외부 dependency 변화 시**: §5 업데이트
5. **해결된 Open Question 은**: §6 에서 §4 (Decisions) 로 이동

**원칙**: "단일 문서 하나만 읽으면 프로젝트 스토리 전체가 파악되어야 함."

---

*Last updated: 2026-04-12 (Phase 1 re-alignment to 2026-04-12 snapshot, M1 Fully Resolved)*
