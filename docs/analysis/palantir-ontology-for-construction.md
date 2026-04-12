# Palantir 가 건설 프로젝트에서 온톨로지를 사용하는 방식

> Source: https://www.palantir.com/offerings/construction/
> 분석 일자: 2026-04-13

---

## 1. 온톨로지의 역할

Palantir 는 온톨로지를 **"단일 의미 계층 (single semantic layer)"** 으로 설명합니다. ERP, BIM, 프로젝트 관리, 회계, 장비 관리 등 **기존 시스템을 교체하지 않고** 그 위에 공통 의미 모델을 얹는 방식입니다.

```
기존 시스템 (건드리지 않음)          Foundry Ontology (의미 통합)
┌─────────────────────┐           ┌─────────────────────────┐
│ ERP (SAP, Oracle)   │──┐        │ Project                 │
│ BIM (Navisworks)    │──┼──────→ │ ├── Activity            │
│ 프로젝트 관리 (P6)   │──┤        │ ├── Equipment           │
│ 회계 시스템          │──┤        │ ├── Material            │
│ 장비 관리           │──┘        │ ├── Subcontractor       │
└─────────────────────┘           │ ├── Contract            │
                                  │ └── Workforce           │
                                  └─────────────────────────┘
```

**핵심**: 온톨로지는 "데이터를 저장하는 곳" 이 아니라 **"부서 간 공통 언어를 정의하는 곳"**.

## 2. Object Types (건설 도메인)

Palantir 가 건설에서 모델링하는 핵심 개체:

| Object Type | 설명 | 데이터 소스 |
|-------------|------|-----------|
| **Project** | 포트폴리오 단위, 예산+일정+이해관계자 | 프로젝트 관리 시스템 |
| **Activity / Task** | WBS 분해 구조 요소 | P6, MS Project |
| **Equipment** | 건설 장비 (크레인, 굴삭기 등) + 가동률 | 장비 관리 시스템 |
| **Material / Part** | 자재 + 재고 + 조달 아이템 | ERP, BIM takeoff |
| **Subcontractor** | 하청업체 + 성과 이력 | 계약 관리 |
| **Workforce / Labor** | 인력 + 타임카드 + 스케줄 | HR, 현장 시스템 |
| **Contract** | 계약서 + 조항 + 변경 이력 | 법무/계약 시스템 |
| **Document** | 도면, 스펙, BIM 모델 | 문서 관리 |

### 우리 프로젝트와의 대응

| Palantir Object Type | 우리 OWL Class | 우리 데이터 |
|---------------------|---------------|-----------|
| Project | — (단일 플랜트) | config.SNAPSHOT |
| Activity / Task | — | ❌ 없음 |
| Equipment (건설장비) | — | ❌ 없음 (BIM Equipment 와 다름) |
| Equipment (플랜트장비) | Equipment + 8 서브클래스 | ✅ 770개, criticality score |
| Material | Material (4종) | ⚠️ 제한적 |
| Subcontractor | — | ❌ 없음 |
| Workforce | — | ❌ 없음 |
| Contract | — | ❌ 없음 |
| Document | — | ❌ 없음 |
| **BIM Object** | **BIMEntity (28 classes)** | **✅ 12,009개** |
| **Pipeline** | **Pipeline (147)** | **✅** |
| **Zone** | **Zone (144)** | **✅** |

**발견**: Palantir 의 Object Type 은 **프로젝트 관리 중심** (일정, 비용, 인력, 계약). 우리는 **BIM 물리 모델 중심** (객체, 공간, 연결). 둘은 서로 다른 계층이고 **상호 보완적**.

## 3. Link Types (관계)

Palantir 가 사용하는 건설 도메인 관계:

| Link Type | From → To | 의미 |
|-----------|----------|------|
| **DecomposesInto** | Project → Activity | WBS 계층 분해 |
| **AllocatedTo** | Resource → Activity | 인력/장비/자재 배정 |
| **PerformedBy** | Activity → Subcontractor | 작업 수행 업체 |
| **BelongsTo** | Equipment → Project | 장비 투입 |
| **SuppliedBy** | Material → Subcontractor | 자재 공급원 |
| **GovernedBy** | Transaction → Contract | 계약 귀속 |
| **PrecededBy** | Activity → Activity | 공정 선후 관계 |

### 우리의 Link Types 와 대응

| Palantir Link | 우리 Link | 대응 수준 |
|-------------|----------|:--------:|
| PrecededBy | **MUST_PRECEDE** (18,214) | ✅ 동일 개념 |
| DecomposesInto | **HAS_PARENT** (12,008) | ✅ 유사 |
| BelongsTo | **BELONGS_TO_PIPELINE** (2,926) | ✅ 도메인 특화 |
| AllocatedTo | **IN_ZONE** (7,840) | ⚠️ 유사 (존 = 작업 패키지) |
| — | **ADJACENT_TO** (220K) | 🆕 Palantir 에 없는 관계 |
| — | **ZONE_PRECEDES** (108) | 🆕 존 간 의존성 |

**발견**: 우리의 `ADJACENT_TO` (공간 인접) 와 `ZONE_PRECEDES` (존 간 시공 순서) 는 Palantir 표준 모델에 **없는** 관계입니다. BIM 데이터에서만 추출 가능한 물리적 관계.

## 4. 온톨로지 기반 워크플로우

Palantir 는 온톨로지 위에 **Action** (워크플로우) 을 구축합니다:

### 4.1 조달 워크플로우
```
Material (재고 부족) 
  → Action: 발주 생성
  → Contract (공급 계약) 확인
  → Subcontractor (벤더) 에 PO 발행
  → 3-way match: PO ↔ 송장 ↔ 입고 자동 대조
```

### 4.2 스케줄 워크플로우
```
Activity (일정 지연)
  → Action: 영향 분석
  → 연결된 Activity 들의 일정 재조정
  → 배정된 Resource (인력/장비) 자동 재배치
  → "자재 배송 지연 시, 인력이 자동으로 다른 작업으로 전환"
```

### 4.3 BIM 연계 워크플로우
```
Document (BIM 3D 모델)
  → Automated Takeoff: 도면에서 자재/부품 자동 추출
  → Material Object 생성
  → 기존 재고와 대조
  → 부족분 조달 워크플로우 시작
```

### 우리가 구현할 수 있는 워크플로우

| 워크플로우 | Palantir 방식 | 우리 가능한 방식 |
|-----------|-------------|---------------|
| BIM Takeoff | 도면에서 자재 추출 | ✅ Gold 에서 commodity_code/spec/material 집계 |
| 시공 순서 조회 | Activity 선후 관계 | ✅ MUST_PRECEDE DAG + Zone ordering |
| 장비 영향 분석 | Equipment → 연결된 Activity | ✅ Equipment criticality → 인접 Pipeline → 존 |
| 자재 존별 배분 | Material → Activity 배정 | ✅ 존별 BOM (commodity_code × zone) |
| 셧다운 범위 | — | ✅ Zone shutdown_impact + valve isolation |

## 5. BIM 과 온톨로지의 연결

Palantir 는 BIM 을 **Document Object** 로 취급합니다 — 3D 모델은 "파싱해서 정보를 추출하는 대상" 이지, 온톨로지의 핵심이 아닙니다. 추출된 정보 (자재, 수량, 스펙) 가 Material/Part Object Type 으로 변환됩니다.

```
BIM 3D Model (Document)
  → Automated Takeoff
  → Material: "150# RF Flange, Carbon Steel, 4" ← Object Type
  → Quantity: 89개
  → 파이프라인: P-10147
  → 존: Zone 15
```

**우리 프로젝트의 차별점**: 우리는 BIM 객체 자체를 Object Type 으로 모델링합니다 (12,009개 각각이 개체). Palantir 는 BIM 을 소스로 사용하지만 개별 객체까지 추적하지는 않을 수 있습니다. 우리의 접근이 **더 세밀한 추적성** 을 제공합니다.

## 6. 핵심 차이와 시사점

| 관점 | Palantir | 우리 프로젝트 |
|------|---------|------------|
| **중심 축** | 프로젝트 관리 (일정, 비용, 인력) | BIM 물리 모델 (객체, 공간, 연결) |
| **데이터 규모** | 엔터프라이즈 (수천 프로젝트) | 단일 플랜트 (12K 객체) |
| **BIM 활용** | 소스 (takeoff 후 폐기) | 코어 (객체 단위 추적) |
| **공간 관계** | 없음 (ADJACENT_TO 없음) | ✅ 220K 간선 (3-tier 분류) |
| **온톨로지 언어** | Foundry 자체 | OWL/RDF (표준) |
| **사용자** | 비개발자 (Workshop 앱) | 개발자/분석가 (API + 노트북) |

### 보완 기회

Palantir 에 **없고** 우리에게 **있는 것**:
1. **객체 단위 공간 인접 관계** → 시공 간섭 분석의 기반
2. **AABB 기반 인접성 3-tier 분류** → 연결 품질 차등화
3. **OWL/SHACL 기반 데이터 품질 검증** → 선언적 규칙
4. **Precedence DAG 자동 생성** → BIM 데이터에서 시공 순서 추론

우리에게 **없고** Palantir 에 **있는 것**:
1. **비용/인력/계약 데이터** → ERP/HR 연동
2. **Workshop 앱** → 비개발자 인터페이스
3. **Action 워크플로우** → 자동화된 의사결정
4. **실시간 현장 데이터** → IoT/모바일 연동

### Foundry 에 올리면 얻는 것

우리의 BIM 온톨로지를 Foundry 에 올리면 **Palantir 에 없던 물리적 계층** 이 추가됩니다:

```
Palantir 표준 건설 온톨로지 (프로젝트 관리)
  │
  └── 우리의 BIM 온톨로지 (물리 모델)     ← Foundry 에 import
      ├── PipingComponent (3,062)
      ├── StructuralMember (4,840)
      ├── Equipment (770)
      ├── adjacentTo (220K)
      ├── mustPrecede (18K)
      └── Zone (144) + KPIs (33)

  → Workshop 에서: "Zone 15 의 시공을 시작하려면 뭐가 필요한가?"
  → Action: 존별 BOM → 조달 워크플로우 시작
  → Action: MUST_PRECEDE → 선행 존 완료 확인
```

---

*Last updated: 2026-04-13*
