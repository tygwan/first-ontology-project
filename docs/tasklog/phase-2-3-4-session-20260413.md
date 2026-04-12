# Session 2026-04-13 — Phase 2/3/4 + Findings M2/M3 + KPIs

**일자**: 2026-04-12 ~ 2026-04-13
**커밋 범위**: `cd11661`..`904aeba` (17 commits)

---

## 1. 언어 / 내용

### Phase 2: OWL Ontology (`2185055`)
- `src/bimkg/ontology/namespaces.py` — BIM/INST/SPATIAL namespace
- `src/bimkg/ontology/schema.py` — 28 OWL classes, 8 object props, 32 data props
- `src/bimkg/ontology/instances.py` — ABox 3 파일: objects 12MB, spatial 12MB, shared 0.1MB
- `tests/test_ontology/` — 59 tests (TBox 33 + ABox 26)

### Phase 3: SHACL Validation (`2a2d242`)
- `src/bimkg/validation/shapes.py` — 6 SHACL shapes
- `src/bimkg/validation/validate.py` — pySHACL runner + ValidationResult
- `tests/test_validation/` — 14 tests

### Phase 4: Graph Analytics (`8b0dcc9`)
- `src/bimkg/analytics/metrics.py` — degree centrality, clustering
- `src/bimkg/analytics/zones.py` — Louvain community detection
- `src/bimkg/analytics/precedence.py` — 3-constraint DAG + adjacency_tier param
- `src/bimkg/analytics/neo4j_export.py` — Neo4j CSV export
- `src/bimkg/analytics/kpi.py` — 33 KPIs (건설 14 + 시설 17 + 공통 2)
- `tests/test_analytics/` — 19 tests

### Findings
- M2: Adjacency AABB 3-tier (`cc7b562`) — Strong/Medium/Weak 분류
- M3: Parent box contamination (`053b6b3`) — is_parent_box 플래그 + 재분석

### Notebooks (5개)
- `01_eda.ipynb` — 컬럼 품질, 클래스 비교, 3D 공간, 파이프라인, 그래프
- `02_construction_management.ipynb` — 양중 지도, 시공 존 A/B (Grid vs Louvain)
- `03_adjacency_tiers.ipynb` — AABB 근거, 3-tier, A/B (88→44), 파이프라인 사례
- `04_construction_schedule.ipynb` — 간트, 공간 파도, 의존성 매트릭스, critical path
- `05_kpi_dashboard.ipynb` — 33 KPI 시각화 (plant/equipment/accessibility/zone/pipeline)

### Infrastructure
- `scripts/neo4j_import.sh` — Docker Neo4j 재현 가능 스크립트
- PNG 저장 규칙 수립 + 노트북 01~04 소급 적용 (25 PNGs)
- 전체 노트북 해석 셀 26개 추가

### Documentation
- `docs/analysis/methodology-data-logic.md` — 12 섹션 데이터 논리 체인
- `docs/findings/2026-04-12-M2-adjacency-tiers/` — M2 아카이브
- `docs/findings/2026-04-13-M3-parent-box-contamination/` — M3 아카이브 + DXTnavis Issue #4

---

## 2. 문제

### M2: Adjacency = AABB 기반
- 220K 간선이 바운딩 박스 겹침 기반 — 물리적 접촉이 아님
- max overlap 41,150 m³ (47m 정육면체) — 시스템 그룹 객체의 BB
- 해결: 3-tier 분류 (Strong touch 13K / Medium small overlap 73K / Weak 48K)
- A/B 결과: critical chain 88 → 53 → 17 steps

### M3: Parent box 448개가 adjacency 66% 오염
- mesh 없음 + bbox > 99pctile = parent box (계층 노드가 물리 객체로 분류됨)
- 최악: `Structure` (Level 1, bbox 103,779 m³, degree 5,267 = 62% 연결)
- 해결: `is_parent_box` 플래그 + `graph_participant` 복합 플래그
- 결과: graph 8,511→7,840, max degree 5,161→388, zones 29→144

### Valve 데이터 부재
- 이 플랜트 데이터에 Valve 객체가 없음 (display_name 에 "valve" 0건)
- Blind Flange + Spectacle blind (57개) 로 격리 분석 대체
- DXTnavis 추출 범위 한계 가능성 — 향후 확인 필요

---

## 3. 분석

### 건설 + 시설 이중 관점
같은 데이터에서 두 가지 관점의 질문을 함:
- 건설: "어떻게 지을 것인가" → BOM, 양중, 시공 순서, 존 간 병행성
- 시설: "지어진 후 어떻게 유지할 것인가" → 장비 임계도, 접근성, 부식, 격리

### A/B 테스트 패턴 정립
3번의 A/B 테스트를 실행:
1. Grid vs Louvain → Louvain 채택 (3/4 metrics)
2. All vs Strong vs Strong+Medium → S+M 채택 (현실적 타협)
3. pre-M3 vs post-M3 → clean graph 채택 (parent box 제거)

이 패턴을 dev-standards R10 으로 추출 예정.

---

## 4. 해결방안

| 항목 | 접근 | 결과 |
|------|------|------|
| OWL 설계 | D10 sibling + Q2~Q8 결정 적용 | 28 classes, 477K triples |
| SHACL | 6 shapes (2 error + 3 warning + 1 info) | 468 violations 탐지 |
| Adjacency tier | 3-tier 분류 + precedence.py param | adjacency_tier="strong_medium" default |
| Parent box | is_parent_box flag + graph_participant | clean graph 7,840 nodes |
| KPIs | kpi.py 모듈 (4 레벨) | 33 KPIs 계산 |
| Notebooks | 5개 + 해석 26셀 + PNG 25개 | GitHub 렌더링 가능 |
| Neo4j | Docker + import script | 재현 가능 |
| DXTnavis | Issue #4 (parent box) | 제출됨 |

---

## 5. 결과

### 테스트
```
305 passed (212 ingest + 59 ontology + 19 analytics + 14 validation + 1 M3)
```

### 산출물 요약

| 카테고리 | 수량 |
|---------|-----:|
| Python 모듈 (src/) | 15 files |
| Test files | 9 files |
| OWL triples | 477K |
| Neo4j edges | 261K |
| SHACL violations | 468 |
| KPIs | 33 (4 levels) |
| Notebooks | 5 |
| PNG figures | 25 |
| Interpretation cells | 26 |
| Findings | 3 (M1 ✅, M2 ✅, M3 ✅) |
| DXTnavis Issues | 2 (#2, #4) |
| Commits (this session) | 17 |
