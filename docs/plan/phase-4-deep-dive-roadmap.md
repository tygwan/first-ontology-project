# Phase 4 Deep Dive Roadmap — 15 아이템 실행 계획

**작성일**: 2026-04-19
**현재 상태**: Phase 2/3 (Foundry Ontology 기본 세팅) ✅ 완료 + Phase 4-α (P-10147/SC-168 case) ✅ 완료
**다음 단계**: 데이터 분석 7종 + AIP 기술 8종 = **15개 아이템 순차 완주**
**원칙**: 각 아이템은 스크립트 + 시각화(필요 시) + markdown 섹션으로 완결. 끝날 때마다 이 문서의 checkbox 갱신.

---

## 🏁 완료된 것

- [x] Phase 2 — Foundry Object Type 3개 (BimObject, BimPipelines, BimPiping) + Interfaces 3개
- [x] Phase 3 — Link Type 4개 (adjacentTo, hasParent, inGroup, belongsToPipeline)
- [x] Finding M6 — registration 5중 원인 + 해결
- [x] 종합 인사이트 리포트 초안 (정정 배너 추가됨 — AI hallucination 발견)
- [x] **Phase 4-α** — P-10147 (AI FDE 주장) vs SC-168 (실제 핫라인) case study + AIP Logic Agent 프롬프트 세트

---

## 📊 A. 데이터 분석 — 7개 (모두 local 실행 가능, 순차 진행)

### [x] A1 — Clash 검출 랭킹 🔥 ✅ 2026-04-19

- **목표**: 110,173 adjacency overlap 중 Top 100 위험 간섭 지점 추출
- **스코어 공식**: 3 lens (composite / cross-type / pressure-weighted) — 단일 스코어의 편향 회피
- **Inputs**: `bim_adjacent_to`, `bim_belongs_to_pipeline`, `bim_pipelines`, 6 Object Type
- **Outputs**:
  - [`docs/analysis/a1-clash-detection-ranking.md`](../analysis/a1-clash-detection-ranking.md)
  - 4 PNG: score distribution / refined_class 매트릭스 / Top100 scatter / 3-lens top10 panel
  - `scripts/analysis_a1_clash_ranking.py`
  - CSV: `data/analysis/a1_clash_ranking_{top100, cross_type_top50, pressure_weighted_top50}.csv`
- **핵심 findings**:
  - 91% edges (80K+) 가 M3 parent-box contamination → 유효 8,108
  - Composite Top 10 = DB_Conduit Run 자기들끼리 (전기실 밀집)
  - Cross-type Top 1 = Slab × Road (106톤 × 45 m³) — civil layer
  - Pressure-weighted Top 2 = **SC-168 Flange/Elbow × TMHandrail** (1,207 kPa × 작업자 동선) ← Phase 4-α 확증
- **Function 후보**: F1 `rank_clashes(pipeline?, lens?, threshold?)` → B3 seed

### [x] A3 — Physical Hub Centrality ✅ 2026-04-19

- **AI FDE hallucination 발견 (5번째)**: "Foundation 221 adj + 620톤" 조합 객체가 **실제 0 개**
- **실제 발견**: 플랜트 물리 허브 Top 20 중 10개가 전부 **Level 6 Slab** — Structure 콘크리트 바닥 슬래브
- **#1**: `BaseSlab-001-0001` (adj 247 + 82.7톤) — 진짜 centrality 최상위
- **A1 연결**: Slab-1-0901 이 A3 허브 Top 2 + A1 cross-type clash #1 (Road 과) — 이중 역할
- **Outputs**:
  - [`docs/analysis/a3-physical-hub-centrality.md`](../analysis/a3-physical-hub-centrality.md)
  - 4 PNG: hub ranking / degree-weight scatter (hallucination marker 포함) / tier refined_class / #1 drill-down
  - `scripts/analysis_a3_physical_hubs.py`
- **Function 후보**: `physical_hubs(top_n, refined_class?)` → B3 seed

### [x] A4 — Material × P × T Adequacy ✅ 2026-04-19

- **데이터 추출**: `sp3d_description` 에서 regex 로 ASTM 재료 파싱 (3,062 중 2,785 / 91%)
- **분포**: Carbon Steel 85.3% / Stainless 304-316 5.4% / Unknown 9%
- **AI FDE hallucination (6번째)**: A106/A312/A234 수치 3종 전부 오류 (inflated + deflated 혼합)
  - A106 Gr.B claim 639 vs actual 92 (7×)
  - A312 TP304 claim 218 vs actual 75 (3×)
  - A234 WPB claim 213 vs actual 680 (역방향 3×)
- **SC-168 재료**: 17 components 전부 Carbon Steel (A106-B / A105 / A234-WPB / A53-B), B31.3 safety margin ~14× (충분)
- **플래그**: Sulphur Recovery 환경 → NACE MR0175 재검토 필요 (SC-168 의 숨은 리스크)
- **Outputs**:
  - [`docs/analysis/a4-material-pt-adequacy.md`](../analysis/a4-material-pt-adequacy.md)
  - 4 PNG: material distribution / P-T regime scatter / stainless pipelines / SC-168 breakdown
  - `scripts/analysis_a4_material_pt.py`

### [x] A5 — Pipeline Balancing ✅ 2026-04-19

- **Typical pipeline (median)**: 13 comp / 2 runs / 826 kg / 미지정 P-T
- **실질 고압 라인은 단 2개**: SC-168 (1,207 kPa), P-005 (670 kPa) — 나머지 48개는 default 0.04 psi
- **66% 가 pressure 미입력** — AI FDE summary 가 왜 오해를 샀는지 재확증
- **Prefix 분류**: `03-/04-` refinery 18 + `PR01-` area 15 + `TRN` 30 + `SC-` 2 + `Uxx-` 9 + Other 45
- **Data quality finding**: pipeline_name = `"Pipelines"` 메타-이름 라인 발견 (153 comp, TRAINING path) → A6 추적 대상
- **Outputs**:
  - [`docs/analysis/a5-pipeline-balancing.md`](../analysis/a5-pipeline-balancing.md)
  - 4 PNG: distribution boxplots / typical vs outliers / prefix groups / profile radar
  - `scripts/analysis_a5_pipeline_balancing.py`

### [x] A6 — Hierarchy Contamination (M3 연장) ✅ 2026-04-19

- **거대 발견**: 12,009 중 **98.8% (11,860) 이 TRAINING 경로** — dataset 전체가 DXTnavis 튜토리얼 샘플 플랜트
- **M3 확장 발견**: bbox > p95 + no_mesh + is_container 조합의 **30개 추가 unflagged contamination** (Tank/Vessel placeholders + Duct Banks + WallSystem)
- **Meta-name 이상**: `pipeline_name = "Pipelines"` L5 라인 유일 이상 (26개 meta-name 은 정상 L4 aggregator)
- **권장 Data Contract**: `is_production` / `is_real_object` / `contamination_score` computed properties 추가
- **Outputs**:
  - [`docs/analysis/a6-hierarchy-contamination.md`](../analysis/a6-hierarchy-contamination.md)
  - 4 PNG: training vs production / flag matrix / level contamination / meta name drill
  - `scripts/analysis_a6_contamination.py`
  - CSV: 30 unflagged candidates + 27 meta-names

### [ ] A7 — 고립 객체 2,790개 분석

- **목표**: `adjacency_count = 0` 객체 2,790개의 정체 분석
- **가설**:
  - 분리 설계 (standalone 장비)
  - 메타 전용 (Container, HierarchyNode)
  - 누락 (mesh 없어 BBox 계산 실패)
- **Inputs**: 6 Object Type + `adjacency_count`
- **Outputs**:
  - `docs/analysis/a7-isolated-objects.md`
  - 3 PNG: refined_class 분포, verdict 교차, bbox_volume vs isolation
  - `scripts/analysis_a7_isolated.py`
- **시간**: 30분

### [ ] A8 — BimPipeRun 흐름 분석

- **목표**: 378 piperun 전수 — 평균 부품 수 (2.6/pipeline), valve/flange 분포 이상치, NPD 계층 분석
- **Inputs**: `bim_piperuns` + `belongsToPipeline`
- **Outputs**:
  - `docs/analysis/a8-piperun-flow.md`
  - 3 PNG: run 크기 분포, NPD 감소율 (pipeline 내), fitting 밀도 outlier
  - `scripts/analysis_a8_piperun.py`
- **시간**: 30분

**A 시리즈 합계**: ~3.5시간, ~16 PNG, ~7 markdown, 7 scripts

---

## 🤖 B. AIP Foundry 기술 시험 — 8개 (Foundry 환경 필요)

### [ ] B1 — AIP Logic Agent 실제 배포

- **목표**: `docs/analysis/aip-logic-agent-prompts-p10147-sc168.md` 의 Q1~Q10 을 실제 Logic Agent 에 연결 + 회귀 테스트
- **Steps**:
  1. AIP Studio → New Logic Agent
  2. Object Type 바인딩 (BimObject, BimPipelines, BimPipeRun, BimPiping)
  3. 시스템 프롬프트 헤더 입력 (faithfulness 규칙)
  4. Q1~Q10 순차 테스트 + 응답 로그 저장
  5. 회귀 세트 (Q8~Q10) 로 hallucination 감지 확인
- **실행 주체**: 사용자 (Foundry UI) + 제가 테스트 프로토콜 준비
- **Outputs**: `docs/analysis/b1-logic-agent-deployment-log.md` (응답 실제 캡처)
- **시간**: 1-2시간

### [ ] B2 — Workshop 대시보드

- **목표**: 3D 뷰어 없이 테이블 + 차트 + 링크 네비 중심 대시보드 5 pages
- **Pages**:
  1. **Overview** — 12,009 objects 분포, refined_class 필터, verdict 품질
  2. **Hotspot Explorer** — SC-168 상세 + Top N hot pipelines (A5 연결)
  3. **Clash Detector** — A1 결과 랭킹 테이블 + 필터
  4. **Material Matrix** — A4 결과 P-T regime map
  5. **Hierarchy Browser** — hasParent tree 탐색 + Foundation (A3) drill-down
- **실행 주체**: 사용자 (Workshop UI) + 제가 page spec markdown 제공
- **Outputs**: `docs/analysis/b2-workshop-dashboard-spec.md` + 실제 Workshop 스크린샷
- **시간**: 2-3시간

### [ ] B3 — AIP Function (TypeScript/Python)

- **목표**: Function 4개 구현
  - **F1** `rank_clashes(pipeline_name?, threshold?)` — A1 기반
  - **F2** `safety_radius(pipeline_name, radius_m)` — centroid + adjacency
  - **F3** `is_training_data(pipeline_name)` — TRN 접두 + null params 판정
  - **F4** `verify_ai_claim(claim_text)` — AI 응답에서 숫자 추출 + SQL 대조
- **실행 주체**: AI FDE 가 Code Repo 에 구현 + 제가 spec
- **Outputs**: `docs/analysis/b3-aip-function-specs.md` + 실제 Foundry Code Repo commits
- **시간**: 2-3시간

### [ ] B4 — AIP Action (NDT 지정 워크플로우)

- **목표**: "Mark pipeline as NDT priority" 액션 버튼 구현
- **Steps**: Object Type 에 `ndt_priority: boolean` property 추가 + Action 으로 토글
- **실행 주체**: 사용자 (Ontology Manager) + 제가 spec
- **Outputs**: `docs/analysis/b4-action-ndt-priority.md`
- **시간**: 1시간

### [ ] B5 — AIP Scenario (What-if 시뮬)

- **목표**: "SC-168 설계 압력 20% 상향 시 인접 구조물 재검토 범위" 시나리오
- **구현**: Scenario 에서 BimPipelines.max_pressure_kpa override → 파생 분석
- **실행 주체**: 사용자 (Scenario UI) + 제가 시나리오 정의
- **Outputs**: `docs/analysis/b5-scenario-sc168-pressure-uplift.md`
- **시간**: 1-2시간

### [ ] B6 — OSDK (Ontology SDK) demo

- **목표**: Python / TypeScript 에서 OSDK 로 온톨로지 쿼리 — 외부 앱 연결 증명
- **Demo**:
  - Python: FastAPI endpoint `GET /pipelines/{name}/clashes`
  - TypeScript: 간단한 Next.js 페이지로 Top N 핫라인 리스트
- **실행 주체**: 제가 local 에서 실행 + 스크린샷
- **Outputs**: `docs/analysis/b6-osdk-demo.md` + `scripts/osdk_demo/` 실제 코드
- **시간**: 1-2시간

### [ ] B7 — Pipeline Builder + Airflow 이식

- **목표**: 기존 `src/bimkg/ingest/exporters/foundry.py` 의 로직을 Foundry Pipeline Builder 로 이식 + Airflow DAG 와 동등성 확인
- **실행 주체**: AI FDE + 사용자
- **Outputs**: `docs/analysis/b7-pipeline-builder-migration.md`
- **시간**: 2-3시간

### [ ] B8 — AIP Studio Agent Builder (설계 검토 어시스턴트)

- **목표**: 복합 Agent — "설계 검토 도우미" — P-T 적합성, Clash 리스크, NDT 우선순위 자동 제안
- **구조**:
  - Logic Agent (B1) + Function (F1-F4) + Scenario (B5) 통합
  - Custom 프롬프트 + tool routing
- **실행 주체**: 사용자 (Studio UI) + 제가 스펙
- **Outputs**: `docs/analysis/b8-agent-builder-design-reviewer.md`
- **시간**: 2-3시간

**B 시리즈 합계**: ~12-20시간, 세션 여러 번 분할

---

## 🔄 진행 순서 제안

### Option A (권장): A 시리즈 블리츠 → B 시리즈 순차
```
1. A1 → A3 → A4 → A5 → A6 → A7 → A8        (local 만, 연속 실행)
       ↓ A 결과 전부 정리되면 ↓
2. B6 OSDK demo                              (local, B 중 유일)
3. B1 Logic Agent 실제 배포                  (Foundry UI)
4. B3 AIP Function 구현                      (AI FDE 코드)
5. B2 Workshop 대시보드                      (A1-A8 결과 기반)
6. B4 Action + B5 Scenario                   (Workshop 위에 얹기)
7. B7 Pipeline Builder                       (infra 이식)
8. B8 Studio Agent (복합)                    (마지막)
```

### Option B: 병행 짝지어 (portfolio 스토리 라인)
```
A1 Clash + B3 F1 Function + B2 Clash Detector page
A3 Foundation + B2 Hierarchy Browser page
A4 Material + B2 Material Matrix page
... 각 A 분석이 B 위젯으로 즉시 이어짐
```

**제 추천: Option A**. 이유 — A 시리즈 결과가 B2 Workshop 의 전체 재료가 되므로 "모든 A 완성 후 B 시작" 이 데이터 일관성 보장.

---

## 📌 현재 위치

- ✅ 완료: Phase 2/3 + Phase 4-α + 이 roadmap 문서
- ⏳ 다음: **A1 Clash 검출 랭킹** 부터 시작

---

## 📂 산출물 컨벤션

- **분석 문서**: `docs/analysis/a{N}-{slug}.md`, `docs/analysis/b{N}-{slug}.md`
- **시각화**: `notebooks/figures/a{N}-{slug}/*.png` (DPI 300)
- **스크립트**: `scripts/analysis_a{N}_{slug}.py` (재현 가능)
- **완료 시**: 이 문서의 checkbox `[ ]` → `[x]` + 각 섹션 산출 링크 추가

---

## 🔗 관련

- [`case-p10147-sc168-deep-dive.md`](../analysis/case-p10147-sc168-deep-dive.md) — Phase 4-α 의 selection 근거
- [`aip-logic-agent-prompts-p10147-sc168.md`](../analysis/aip-logic-agent-prompts-p10147-sc168.md) — B1 의 시드
- [`bim-kg-insights-20260417.md`](../analysis/bim-kg-insights-20260417.md) — hallucination 경고 배너 포함 원본 리포트
- [`PROJECT-JOURNAL.md`](../PROJECT-JOURNAL.md) — Timeline 에서 각 완료 지점 기록
- [`phase-2-3-ontology-registration-20260417.md`](../tasklog/phase-2-3-ontology-registration-20260417.md) — Phase 2/3 completion
