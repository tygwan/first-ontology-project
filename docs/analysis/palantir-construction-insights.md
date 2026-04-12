# Palantir Construction Management — 인사이트 + 우리 프로젝트 매핑

> Source: https://www.palantir.com/offerings/construction/
> Date: 2026-04-13

---

## 1. Palantir 가 풀고 있는 건설 관리 문제

| 문제 영역 | Palantir 접근 | 우리 프로젝트에서 해당하는 것 |
|-----------|-------------|--------------------------|
| **데이터 파편화** | 도면/스펙/이력을 통합 플랫폼에 | ✅ 11개 원본 → Medallion 4계층 → 218 cols Gold |
| **수동 조달** | 3-way match, 벤더 성과표 | ⚠️ 자재 데이터 있음 (material 4, spec 10, commodity 83) but 조달 로직 없음 |
| **인력 관리** | 디지털 타임카드, 리소스 예측 | ❌ man-hour 데이터 없음 |
| **장비 활용** | 가동률 분석, 자동 배차 | ⚠️ Equipment 770개 위치+무게 있음, 가동률은 없음 |
| **시공 일정** | 스케줄 통합 (장기/주간/일일) | ✅ Precedence DAG (44 steps), Zone ordering (144존) |
| **자재 부족** | 수요 예측, min/max 모델링 | ⚠️ BOM 집계 가능 (존별 자재), 수요 예측은 불가 |
| **현장-사무실 격차** | 실시간 데이터 흐름 | ✅ FastAPI + Neo4j + LLM agent 로 실시간 질의 가능 |
| **예산 초과** | 실시간 원가 분석 | ❌ 비용 데이터 없음 |

## 2. Palantir 의 핵심 기능 vs 우리의 구현

### 이미 구현한 것

| Palantir 기능 | 우리의 대응 |
|-------------|-----------|
| BIM 시스템 통합 | ✅ DXTnavis → OWL/Neo4j/SQLite 통합 파이프라인 |
| 3D 모델 기반 분석 | ✅ centroid 3D 좌표 + 공간 시공 파도 시각화 |
| 디지털 트윈 | ✅ OWL 온톨로지 (477K triples) = 의미적 디지털 트윈 |
| 공급망 가시화 | ✅ 147 Pipeline, 334 PipeRun, 83 Commodity Code 매핑 |
| 스케줄 통합 | ✅ Precedence DAG → Zone ordering → 간트 차트 |
| 하청 가시화 | ⚠️ Zone 별 작업 패키지 정의 (하청 배분의 기반) |
| 자재 배분 | ✅ 존별 BOM 집계 (material, spec, weight) |

### 구현할 수 있는 것 (데이터 있음, 로직 미구현)

| Palantir 기능 | 필요한 추가 작업 |
|-------------|---------------|
| 벤더 성과표 | commodity_code 별 spec 준수율 분석 |
| 장비 크리티컬리티 | ✅ 이미 equipment_criticality_score 구현 |
| 자재 수요 예측 | zone install_rank 에 따른 자재 납기 우선순위 |
| 리스크 평가 | corrosion_risk_index + 접근성 지수 → 종합 리스크 |

### 구현 불가능한 것 (데이터 없음)

| Palantir 기능 | 누락 데이터 |
|-------------|-----------|
| 실시간 원가 분석 | 단가, 투입 비용 |
| 디지털 타임카드 | 인력 투입 이력 |
| 장비 가동률 | 운영 시간 데이터 |
| AP/AR 자동화 | 재무 데이터 |
| 변경 주문 관리 | 변경 이력 |

## 3. Palantir 가 주장하는 성과 지표

| 지표 | 값 | 우리 프로젝트에서의 대응 |
|------|------|----------------------|
| 공급망 절감 | $161M / 3년 | 측정 불가 (비용 데이터 없음), but 존별 BOM 으로 낭비 식별 가능 |
| 조달 비용 절감 | $126M (315% ROI) | 측정 불가 |
| 디지털 트윈 구축 | "수 일 내" | ✅ 파이프라인 전체 실행 67초 (1분 내 재생성) |
| 자재 부족 감소 | 40% | 측정 불가, but BOM 사전 집계로 예방 가능 |
| 자재 배분 시간 | 주 → 분 | ✅ `kpi_summary("pipeline P-10147")` = 즉시 응답 |
| 보고 주기 | 일 → 실시간 | ✅ FastAPI + LLM = 실시간 자연어 질의 |
| 타임카드 수집 | 1시간 → 5분 | 해당 없음 (인력 데이터 없음) |

## 4. Foundry Ontology 매핑 전략

Palantir Foundry 의 핵심은 **Ontology** — Object Type + Link Type 으로 데이터를 의미적으로 구조화. 우리 OWL 온톨로지가 직접 매핑됩니다.

### Object Types (Foundry)

| Foundry Object Type | 소스 파일 | PK | Title | 행 수 |
|--------------------|---------:|:---:|-------|------:|
| PipingComponent | piping.parquet | object_id | display_name | 3,062 |
| StructuralMember | structural.parquet | object_id | display_name | 4,840 |
| Equipment | equipment.parquet | object_id | display_name | 770 |
| ElectricalComponent | electrical.parquet | object_id | display_name | 1,053 |
| HvacComponent | hvac.parquet | object_id | display_name | 125 |
| UncategorizedObject | other.parquet | object_id | display_name | 2,159 |

### Link Types (Foundry)

| Foundry Link Type | 소스 파일 | From → To | 행 수 |
|------------------|--------:|----------|------:|
| AdjacentTo | adjacent_to.parquet | object → object | 110,173 |
| HasParent | has_parent.parquet | child → parent | 12,008 |
| BelongsToPipeline | belongs_to_pipeline.parquet | object → pipeline | 2,926 |
| InGroup | in_group.parquet | object → group | 12,009 |

### 추가 가능한 Object/Link Types

| Type | 소스 | 설명 |
|------|------|------|
| Pipeline (Object) | sp3d_pipeline 고유값 | 147개 파이프라인 개체 |
| Zone (Object) | Louvain community | 144개 시공 존 |
| MustPrecede (Link) | precedence DAG | 18,214 시공 선후 관계 |
| InZone (Link) | zone_map | 7,840 존 소속 |

## 5. 핵심 인사이트

**Palantir 의 가치 제안은 "데이터 통합 + 의미 모델링 + 실시간 의사결정 지원"** 이며, 이것은 우리가 이 프로젝트에서 구축한 것과 정확히 같은 패턴입니다:

```
Palantir: 파편화된 건설 데이터 → Foundry Ontology → Workshop 앱 → 현장 의사결정
우리:     DXTnavis BIM 데이터 → OWL/Neo4j Ontology → FastAPI/LLM → 시공 계획/시설 관리
```

**차이점**: Palantir 는 엔터프라이즈급 (수천 유저, 실시간 ERP 연동, 비용 관리). 우리는 단일 플랜트 프로토타입 (12K 객체, 분석 중심).

**Foundry 에 올리면 추가되는 것**:
- Workshop 앱으로 비개발자도 데이터 탐색 가능
- Action 으로 "이 존의 시공 시작" 같은 워크플로우
- 다른 Foundry 데이터셋과 Join (ERP, HR, 재무)
- 버전 관리된 Ontology (스키마 변경 추적)

---

*Last updated: 2026-04-13*
