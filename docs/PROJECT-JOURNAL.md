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
- Phase 0 ~ 1d: ✅ 완료 (192 테스트 통과)
- 발견된 데이터 이슈: 🟠 1건 MAJOR (Open), 알려진 한계 3건
- DXTnavis 원천 PR: 📬 [Issue #2](https://github.com/tygwan/DXTnavis/issues/2) 제출됨
- 다음 단계: Phase 1e (M1 해결) 또는 Phase 2 (OWL 온톨로지)

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
| M1 | 2026-04-12 | 🟠 MAJOR | XLSX substring matching misclassifies 997 Piping objects | 🔄 Open | [archive](findings/2026-04-12-M1-piping-misclassification/README.md) |

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
             PROJECT-JOURNAL.md created (this document)                  (pending)
```

### Test count progression

| Phase | Test count | Cumulative |
|-------|-----------:|-----------:|
| 0 | +3 | 3 |
| 1b | +44 | 47 |
| 1a (config + oracle) | +32 | 79 |
| 1a (clean + loader + sqlite) | +73 | 149 |
| 1d (exporters) | +43 | 192 |

---

## 3. Findings (상세)

### M1. XLSX substring matching misclassifies 997 Piping objects  🟠 MAJOR — 🔄 Open

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

**외부 조치**: [DXTnavis Issue #2](https://github.com/tygwan/DXTnavis/issues/2) 제출됨 (2026-04-12).

**해결 방향**: Phase 1e (로컬 `classification_confidence` 컬럼 추가) + DXTnavis 원천 C# 수정 병행.

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
- 현재 2026-04-07 스냅샷 고정
- 🔴 알려진 버그: M1 (Issue #2 제출)
- 🟡 Data extraction wishlist (Issue #2 Part 2): ParentId 보존, Parquet 옵션, 관계 시트 등

**연락 채널**: GitHub Issues on tygwan/DXTnavis

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

### Q1. M1 해결 전 Phase 2 시작?

**질문**: Phase 1e 로 `classification_confidence` 컬럼을 먼저 추가한 후 Phase 2 를 시작할지, 아니면 Phase 2 온톨로지 설계 시 M1 보정을 포함할지.

**찬 / 반**:
- Phase 1e 먼저: 명시적, 테스트 가능. 그러나 Phase 1d 출력물 재생성 필요 (0.5일).
- Phase 2 통합: 재작업 감소. 그러나 Phase 2 설계 복잡도 증가.

**상태**: 사용자 결정 대기.

### Q2. DXTnavis Issue #2 응답 대기 시간?

**질문**: DXTnavis 측 수정 완료까지 얼마나 기다릴지? 장기간이면 우리 쪽에서 우회 해결 (Python classifier override) 필요.

**상태**: 열려 있음. 원천 수정이 늦어지면 Option 2 (confidence column) 장기 유지.

### Q3. Phase 2 OWL 온톨로지 스키마 top-level 구조?

**질문**: `BIMEntity > BIMObject > PhysicalObject` vs `BIMObject ‖ AnalysisArtifact` (sibling) ?

**이전 논의**: [`docs/analysis/phase-1a-data-realignment-design.md`](analysis/phase-1a-data-realignment-design.md) §4.3 에서 sibling 구조를 권고했으나 최종 결정은 Phase 2 시작 시.

---

## 7. Where to find what

### 빠른 참조 테이블

| 찾고 싶은 것 | 위치 |
|------------|------|
| 전체 프로젝트 개요 | [`README.md`](../README.md) |
| Phase 구현 계획 | [`docs/plan/pipeline-implementation-plan.md`](plan/pipeline-implementation-plan.md) |
| Phase 1a 설계 논의 | [`docs/analysis/phase-1a-data-realignment-design.md`](analysis/phase-1a-data-realignment-design.md) |
| XLSX classifier 로직 분석 | [`docs/analysis/refined-xlsx-exporter-logic.md`](analysis/refined-xlsx-exporter-logic.md) |
| Phase 1 검증 가이드 | [`docs/analysis/phase-1-verification-guide.md`](analysis/phase-1-verification-guide.md) |
| 완료된 Phase 별 기록 | [`docs/tasklog/`](tasklog/) |
| 발견된 이슈 아카이브 | [`docs/findings/`](findings/) |
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
| Bronze (raw) | `data/raw/dxtnavis/2026-04-07/` | CSV, XLSX, JSON (읽기 전용) |
| Silver (clean) | `data/clean/2026-04-07/` | Parquet |
| Gold (enriched) | `data/enriched/2026-04-07/` | Parquet + SQLite |
| PowerBI | `data/powerbi/2026-04-07/` | CSV |
| Ontology | `data/ontology/2026-04-07/{object_types,link_types,owl}/` | Parquet / TTL |
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

*Last updated: 2026-04-12 (M1 finding + archive rule 수립 시점)*
