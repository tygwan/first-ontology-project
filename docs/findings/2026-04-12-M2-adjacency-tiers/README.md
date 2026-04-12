# 2026-04-12 — M2 — Adjacency 는 AABB 기반이며 3단계 품질 분류가 필요

**Severity**: 🟡 MINOR
**Status**: ✅ **Resolved** (3단계 분류 도입, precedence DAG 에 적용)
**Discovered by**: Phase 4 Graph Analytics — Neo4j 탐색 중
**Affects**: Phase 4 precedence DAG, 시공 순서 분석, 향후 SHACL 검증 규칙

---

## 1. Finding

DXTnavis 의 adjacency 220,346 간선은 **바운딩 박스(AABB) 기반 근접 판정**이며, 물리적 표면 접촉이 아닙니다. 이 간선들을 동일하게 취급하면 precedence DAG 에 과도한 순서 제약이 생겨 critical chain 이 5배 이상 부풀려집니다.

**정량 영향**:
- 전체 220K 간선으로 precedence → critical chain **88 steps** (과도하게 보수적)
- Strong (touch) 13K 만으로 → **17 steps** (최소 필수 순서)
- Strong+Medium 87K → **53 steps** (현실적 타협점)

## 2. Evidence

**노트북**: [`notebooks/03_adjacency_tiers.ipynb`](../../../notebooks/03_adjacency_tiers.ipynb)

시각화 포함:
- relation_type 분포, overlap volume 분포 (log scale), tolerance 분포
- 3단계 분류별 cross-class adjacency 패턴
- A/B 테스트: 분류별 DAG 간선 수 / critical chain 길이 비교
- 사례 연구: Pipeline U01-UA-2001 설치 순서

**핵심 근거**: max overlap 41,150 m³ = 한 변 34.5m 정육면체. 시스템 레벨 그룹 객체 (B01-PipingSys-Process 등) 의 BB 겹침.

## 3. Analysis

### 3.1 Root cause

DXTnavis 는 Navisworks API 의 `FindClashes` 를 tolerance 0.15m (93% 의 간선) 로 호출하여 AABB 기반 근접 판정 수행. 세 가지 relation_type 을 리턴:

| Type | 간선 수 | 거리 범위 | 겹침 범위 | 물리적 의미 |
|------|--------:|-----------|----------|-----------|
| overlap | 175,106 | 0 | 0~41,150 m³ | BB 가 겹침 (크기 무관) |
| touch | 13,422 | ≈0 | 0 | 표면이 맞닿음 |
| neartouch | 31,818 | 0.1mm~19cm | 0 | 근접하지만 접촉 아님 |

### 3.2 3단계 분류

| 등급 | 조건 | 간선 수 | CM 해석 |
|------|------|--------:|---------|
| **Strong** | touch | 13,422 | 볼트/용접/플랜지 — 필수 순차 시공 |
| **Medium** | overlap < 0.01 m³ | 73,222 | 관통부/접합 — 간섭 조율 |
| **Weak** | overlap > 1 m³ 또는 neartouch | 47,786 | 공간 인접 — 순서 무관 |

### 3.3 Impact

- precedence DAG 에서 adjacency_interference 간선이 전체 간선의 99% 차지 (class_order 와 vertical 은 각각 80, 253 개)
- Weak 간선이 포함되면 시스템 그룹 객체끼리의 가짜 간섭이 real chain 을 늘림
- Strong-only 분석은 "물리적 연결점 기반 최소 시공 순서" 를 제공

## 4. Resolution

### 4.1 적용

- `notebooks/03_adjacency_tiers.ipynb` 에 3단계 분류 + A/B 비교 기록
- Phase 4 precedence.py 는 현재 전체 adjacency 를 사용 → 향후 tier 필터 파라미터 추가 가능
- Neo4j 에 `relationType` 속성 추가 완료 → Cypher 에서 `WHERE r.relationType = "touch"` 로 필터 가능

### 4.2 Action items

- [x] 3단계 분류 정의 및 A/B 테스트 (이 finding)
- [x] 노트북에 시각화 + 사례 연구 기록
- [x] Neo4j adjacency 간선에 relationType, distanceM, overlapM3 속성 추가
- [ ] precedence.py 에 `adjacency_tier` 파라미터 추가 (default="strong_medium")
- [ ] Phase 3 SHACL 에서 "Strong 연결이 없는 고립 PhysicalObject" 규칙 추가

## 5. References

- **노트북**: [`notebooks/03_adjacency_tiers.ipynb`](../../../notebooks/03_adjacency_tiers.ipynb)
- **Source data**: `data/enriched/2026-04-12/bim_adjacency_sym.parquet`
- **DXTnavis adjacency 원본**: `data/raw/dxtnavis/2026-04-12/adjacency.csv`
- **Phase 4 precedence**: `src/bimkg/analytics/precedence.py`
- **Neo4j export**: `src/bimkg/analytics/neo4j_export.py`
- **관련 finding**: M1 (classification) — adjacency 데이터의 두 번째 품질 이슈
