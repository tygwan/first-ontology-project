# 2026-04-13 — M3 — Parent box 객체가 adjacency 의 66% 를 오염

**Severity**: 🟠 MAJOR
**Status**: 🔄 Fixing (is_parent_box 플래그 추가 + 재분석 진행 중)
**Discovered by**: Phase 4 인접성 판정 기준 심층 조사
**Affects**: adjacency graph, Louvain zones, precedence DAG, critical chain, Neo4j

---

## 1. Finding

271개 객체가 `is_container=False`, `is_analysis_volume=False` (물리 객체 취급) 이지만 **mesh 가 없고 bbox 가 비정상적으로 큼**. 이들은 계층 노드/시스템 그룹 객체로, 실제 물리 부품이 아니라 **하위 객체들의 bbox 합산** 을 갖고 있음.

**정량 영향**:
- 271개 parent box 객체가 adjacency 간선 **145,346개 (66%)** 에 관여
- 최악 사례: `Structure` (Level 1, bbox 103,779 m³ = 47m 정육면체, degree 5,267 = 물리 객체의 62%)
- `A2` (Level 2, bbox 209,726 m³), `U15` (Level 3, bbox 144,375 m³)
- 우리의 Louvain zones (29존) 과 precedence DAG (53 steps) 가 이 오염 위에서 실행됨

**추가 오염**: AnalysisVolume 145개가 5,138 간선으로 물리 객체와 인접 (시공에 무의미)

## 2. Evidence

**식별 기준**: `has_real_mesh == False AND bbox_volume_m3 > 36.34 m³` (mesh 있는 물리 객체의 99th percentile)

| 지표 | Mesh 있는 물리 객체 | Parent box (mesh 없음) |
|------|--------------------:|---------------------:|
| 개수 | 7,840 | 271 |
| bbox median | 0.038 m³ | 10.3 m³ |
| bbox mean | 2.9 m³ | 1,598 m³ |
| bbox max | 3,005 m³ | 209,726 m³ |
| adjacency degree mean | 25.0 | 278 |
| adjacency degree max | ~300 | 5,267 |

**오염 규모**:
- 전체 220,346 간선 중 145,346 (66%) 가 parent box 관여
- Clean 간선 (parent box + AV 모두 제외): 73,128 (33%)

## 3. Analysis

### 3.1 Root cause

DXTnavis 가 Navisworks 모델의 **모든 객체**를 adjacency.csv 에 포함. 계층 노드 (Level 0~3 의 시스템 폴더, 영역 구분 객체) 도 AABB 근접 판정에 참여. 이들의 bbox 는 하위 객체 전체를 감싸므로 거의 모든 하위 객체와 overlap.

### 3.2 왜 이전에 발견 안 됐는가

- `is_container` 플래그로 3,353개를 걸러냈지만, 이 271개는 container 판정 기준에 걸리지 않음
- 이유: `is_container` 는 validation.csv 의 verdict 기반인데, 이 271개는 validation.csv 에서 다른 verdict 를 받음
- `has_real_mesh=False` 는 확인했지만 bbox 크기와 교차 분석하지 않음

### 3.3 DXTnavis 측 논의 필요 사항

| 요청 | 이유 |
|------|------|
| adjacency.csv 에서 mesh 없는 객체 제외 | 가장 안전 — hierarchy 는 보존, adjacency 만 정리 |
| 또는 `has_geometry` 컬럼 추가 | 우리가 필터 가능 |
| 271개 객체의 정체 확인 | 계층 노드? aggregation box? 설계 보조? |
| 제외 시 connected_groups 영향 확인 | 그룹 구조 변경 가능 |

## 4. Resolution

### 4.1 접근: Raw 유지 + 전처리 필터 (Phase 1e 패턴)

- Raw 데이터 변경 없음 (R9 provenance)
- `clean.py` 에 `is_parent_box` 플래그 추가
- 판정 기준: `has_real_mesh == False AND bbox_volume_m3 > (mesh 있는 객체의 99th percentile)`
- 분석 모듈에서 parent_box 제외

### 4.2 Action items

- [x] Finding M3 아카이브
- [x] `clean.py` 에 `is_parent_box` 플래그 추가 (`053b6b3`)
- [x] Phase 1a 재실행 (Gold 재생성 — 448 parent box 식별)
- [x] Phase 1d exporter 재실행
- [x] Phase 2 ABox 재생성 (parent_box → HierarchyNode 타입)
- [x] 테스트 재기준선 (305 passing, +1 new)
- [x] PROJECT-JOURNAL 업데이트 (M3 행 추가)
- [ ] Phase 4 analytics 재실행 (clean graph 기반 — 7,840 nodes)
- [ ] Neo4j 재로드
- [ ] DXTnavis Issue 초안 작성

## 5. References

- **관련 finding**: M2 (adjacency AABB 기반 — 3-tier 발견 시 이 문제의 전조)
- **데이터**: `data/enriched/2026-04-12/bim_adjacency_sym.parquet`
- **분석 코드**: `src/bimkg/analytics/metrics.py` (degree 5,267 이 여기서 나옴)
- **기존 baseline insights**: `docs/reference/dxtnavis-2026-04-07-baseline-insights.md` Insight 8 에서 degree 5,267 이상치를 이미 언급했었음 — 그때 root cause 를 파악하지 못함
