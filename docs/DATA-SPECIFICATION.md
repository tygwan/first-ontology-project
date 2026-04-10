# Ontology for CM - Data Specification

> DXTnavis v1.8.0으로 추출한 BIM 데이터 3종의 구조와 특성을 정리한 문서입니다.
> 추출일: 2026-03-23 | 소스: Navisworks NWD (SP3D 기반 플랜트 모델)

---

## 파일 목록

| # | 파일 | 형식 | 크기 | 행수 | 설명 |
|---|------|------|------|------|------|
| 1 | `AllProperties_20260323_063038.csv` | CSV (UTF-8) | - | 12,009 objects | 전체 객체의 모든 속성 (raw) |
| 2 | `Refining_ObjectID_20260323_063058.xlsx` | XLSX | 2.5 MB | 12,009 objects | 정제된 피벗 형태 + 요약 시트 |
| 3 | `pipeline_schedule_20260323_063138.csv` | CSV (CP949) | - | 378 tasks | TimeLiner 4D 시뮬레이션 스케줄 |

---

## 1. AllProperties CSV

### 개요

모델의 **모든 객체 x 모든 속성**을 flat CSV로 추출한 원본 데이터입니다.
1행 = 1객체, 속성이 없는 셀은 빈 문자열입니다.

- **총 객체**: 12,009개
- **총 컬럼**: 136개
- **인코딩**: UTF-8 (BOM)

### 컬럼 구조 (4개 카테고리, 136 컬럼)

#### Meta (4 컬럼) — 객체 식별 정보

| 컬럼 | 설명 |
|------|------|
| `ObjectId` | 객체 고유 GUID (InstanceGuid 또는 Synthetic ID) |
| `ParentId` | 부모 객체 GUID (계층 구조 보존) |
| `Level` | 계층 깊이 (L0=루트 ~ L9=말단) |
| `객체이름` | 객체 표시 이름 |

#### SmartPlant 3D (96 컬럼) — SP3D 엔지니어링 속성

| 분류 | 속성 | 채움률 | 설명 |
|------|------|:------:|------|
| **식별** | Name | 65.7% | 객체 이름 |
| | SP3d Moniker | 65.7% | SP3D 내부 식별자 |
| | System Path | 65.7% | 계층 경로 |
| | Permission Group ID | 61.1% | 권한 그룹 |
| **상태** | Status | 61.5% | 객체 상태 |
| | Date Created | 61.5% | 생성일 |
| | Date Last Modified | 61.5% | 수정일 |
| | User Created | 61.1% | 생성자 |
| | User Last Modified | 61.1% | 수정자 |
| | Reporting Type | 57.5% | 보고 유형 (MTO 포함/제외) |
| | Construction Type | 51.4% | 시공 유형 (New/Future) |
| **배관** | Pipeline | 24.4% | 파이프라인 이름 (예: P-015) |
| | PipeRun | 24.4% | 파이프런 이름 |
| | NPD | 24.4% | Nominal Pipe Diameter |
| | Flow Direction | 24.4% | 유체 흐름 방향 |
| | Iso Sheet No | 24.4% | ISO 도면 번호 |
| | ShortCode | 24.4% | 부품 코드 |
| | Spool | 24.4% | 스풀 번호 |
| | Stress System No | 24.4% | 응력 해석 번호 |
| | Commodity Code | 26.0% | 자재 코드 |
| | Commodity Option | 24.4% | 자재 옵션 |
| | Design Max Pressure | 24.4% | 설계 최대 압력 |
| | Design Max Temperature | 24.4% | 설계 최대 온도 |
| **위치/크기** | Location | 42.1% | 위치 정보 |
| | Length | 14.5% | 길이 |
| | Width | 14.8% | 너비 |
| | Depth | 13.0% | 깊이 |
| | Cut Length | 13.0% | 절단 길이 |
| | Cardinal Point | 13.0% | 기준점 |
| | Section Name | 13.0% | 단면 이름 |
| **중량** | Dry Weight | 44.7% | 건조 중량 |
| | Wet Weight | - | 습윤 중량 |
| | Weight | - | 중량 |
| | DryCGX/Y/Z | - | 건조 무게중심 좌표 |
| | WetCGX/Y/Z | - | 습윤 무게중심 좌표 |
| **자재** | Material | 20.0% | 자재 |
| | Material Grade | - | 자재 등급 |
| | Material Name | - | 자재 이름 |
| | Material Type | - | 자재 유형 |
| | Specification | 6.1% | 사양 |
| | Spec Name | 5.1% | 사양 이름 |
| **장비** | Equipment Name | - | 장비 이름 |
| | Eqp Type 0~3 | - | 장비 유형 분류 |
| **방화/보온** | Fire Rating | - | 방화 등급 |
| | Fireproofing Label | 6.1% | 방화 라벨 |
| | Insulation Material | - | 보온재 |
| | Insulation Purpose | - | 보온 목적 |
| | Insulation Thickness | - | 보온 두께 |
| **기타** | Description | 28.7% | 설명 |
| | BOM description | 6.0% | BOM 설명 |
| | Reference | 13.0% | 참조 |
| | Rating | - | 등급 |
| | Encasement | 6.1% | 외장 |
| | Support Assembly | 6.0% | 서포트 어셈블리 |
| | Support Location | 6.0% | 서포트 위치 |

#### 재질 (14 컬럼) — Navisworks 렌더링 색상

| 속성 | 설명 |
|------|------|
| 분산.빨간색/녹색/파란색 | Diffuse RGB |
| 반사.빨간색/녹색/파란색 | Specular RGB |
| 발광.빨간색/녹색/파란색 | Emissive RGB |
| 주변.빨간색/녹색/파란색 | Ambient RGB |
| 광택 | Shininess |
| 투명도 | Transparency |

#### 항목 (14 컬럼) — Navisworks 내부 메타데이터

| 속성 | 설명 |
|------|------|
| GUID | Navisworks 내부 GUID |
| 유형 / 내부 유형 | 객체 유형 |
| 이름 | 표시 이름 |
| 아이콘 | 아이콘 유형 |
| 소스 파일 / 소스 파일 이름 / 파일 이름 | 원본 파일 정보 |
| 도면층 | 레이어 |
| 단위 | 단위 체계 |
| 재질 | 재질 이름 |
| 작성자 | 작성자 |
| 숨김 | 숨김 상태 |
| 필수 | 필수 여부 |

#### 형상 (8 컬럼) — 3D 기하 요소 통계

| 속성 | 설명 |
|------|------|
| 삼각형 | Triangle 개수 |
| 기본체 | Primitive 개수 |
| 솔리드 | Solid 개수 |
| 조각 | Fragment 개수 |
| 선 / 점 / 스냅점 / 문자 | 기타 기하 요소 |

### 계층 구조 분포

| Level | 객체 수 | 설명 |
|:-----:|--------:|------|
| L0 | 1 | 루트 |
| L1 | 4 | 분야 (Process, Structural, ...) |
| L2 | 144 | Pipeline, Equipment Group |
| L3 | 34 | Sub-group |
| L4 | 116 | PipeRun, Member System |
| L5 | 640 | 컴포넌트 그룹 |
| L6 | 3,320 | Geometry Group |
| L7 | 4,460 | 개별 부품 (주요 데이터) |
| L8 | 2,968 | 하위 기하 요소 |
| L9 | 322 | 말단 요소 |

### 객체 분류 분포

| Class | 객체 수 | 비율 |
|-------|--------:|-----:|
| Structure | 5,926 | 49.3% |
| Piping | 4,014 | 33.4% |
| Equipment | 851 | 7.1% |
| Other | 697 | 5.8% |
| Electrical | 449 | 3.7% |
| HVAC | 72 | 0.6% |
| **Total** | **12,009** | **100%** |

---

## 2. Refined XLSX

### 개요

AllProperties CSV를 정제하여 카테고리 접두사(`DisplayString:`, `SmartPlant 3D|`) 를 제거하고,
피벗 형태로 재구성한 Excel 파일입니다. 5개 시트로 구성됩니다.

- **크기**: 2.5 MB
- **시트 수**: 5개

### Sheet 1: Refining_ObjectID_Pivot (메인 데이터)

**12,009행 x 66컬럼** — 1행 = 1객체, 정제된 속성

| # | 컬럼 | 분류 | 설명 |
|---|------|------|------|
| 1 | Class | 식별 | 객체 분류 (Structure/Piping/Equipment/...) |
| 2 | ObjectId(GUID) | 식별 | 고유 GUID |
| 3 | DisplayName | 식별 | 표시 이름 |
| 4 | System Path | 식별 | 계층 경로 |
| 5 | Level | 식별 | 계층 깊이 |
| 6 | Status | 상태 | 객체 상태 |
| 7 | Permission Group ID | 상태 | 권한 그룹 |
| 8 | Pipeline | 배관 | 파이프라인 이름 |
| 9 | PipeRun | 배관 | 파이프런 이름 |
| 10 | RunName | 배관 | 런 이름 |
| 11 | Spec Name | 배관 | 사양 이름 |
| 12 | Specification | 배관 | 사양 |
| 13 | NPD | 배관 | 공칭 파이프 직경 |
| 14 | Size | 배관 | 크기 |
| 15 | Description | 일반 | 설명 |
| 16 | Construction Type | 시공 | 시공 유형 |
| 17 | Location | 위치 | 위치 |
| 18-21 | Material / Grade / Name / Type | 자재 | 자재 정보 |
| 22 | Equipment Name | 장비 | 장비 이름 |
| 23-30 | BOM desc, Cardinal Pt, ... | 상세 | 상세 속성 |
| 31-32 | Design Max Pressure / Temperature | 설계 | 설계 조건 |
| 33-35 | Dry Weight / Wet Weight / Weight | 중량 | 중량 정보 |
| 36-57 | End Prep ~ Support Location | 상세 | 배관/구조 상세 속성 |
| 58 | Type | 일반 | 유형 |
| 59-63 | Item GUID ~ Source File | 메타 | Navisworks 메타데이터 |
| 64-66 | Triangles / Primitives / Lines | 형상 | 3D 기하 요소 수 |

### Sheet 2: Pipeline_Summary

**147행 x 6컬럼** — 파이프라인별 요약

| 컬럼 | 설명 | 예시 |
|------|------|------|
| Pipeline | 파이프라인 이름 | 03-BFW-2001 |
| Objects | 소속 객체 수 | 18 |
| PipeRuns | PipeRun 수 | 1 |
| Primary NPD | 주요 공칭 직경 | 6in x 6in |
| All NPDs | 모든 직경 | 6in x 6in, 4in x 2in |
| Specs | 사양 | - |

### Sheet 3: Class_Distribution

**6행 x 3컬럼** — 객체 분류별 분포

| Class | Count | Percentage |
|-------|------:|----------:|
| Structure | 5,926 | 49.3% |
| Piping | 4,014 | 33.4% |
| Equipment | 851 | 7.1% |
| Other | 697 | 5.8% |
| Electrical | 449 | 3.7% |
| HVAC | 72 | 0.6% |

### Sheet 4: Equipment_Summary

**110행 x 3컬럼** — 장비별 요약

| 컬럼 | 설명 |
|------|------|
| Equipment Name | 장비 이름 |
| Objects | 소속 객체 수 |
| Types | 포함된 유형 |

### Sheet 5: PipeRun_Detail

**334행 x 6컬럼** — PipeRun 상세

| 컬럼 | 설명 |
|------|------|
| PipeRun | PipeRun 이름 |
| Pipeline | 소속 Pipeline |
| Objects | 소속 객체 수 |
| Primary NPD | 주요 직경 |
| Spec | 사양 |
| Component Types | 포함된 부품 유형 |

---

## 3. Pipeline Schedule CSV

### 개요

Pipeline 4D 기능으로 생성한 **TimeLiner Import용 스케줄 CSV**입니다.
Navisworks TimeLiner Field Selector의 필드명과 1:1 대응합니다.

- **총 Task**: 378개
- **Pipeline 수**: 147개
- **인코딩**: CP949 (한국어 Navisworks 호환)
- **스케줄 기간**: 2026-03-24 ~ 2028-10-28

### 컬럼 구조

| 컬럼 | TimeLiner 필드 | 설명 | 예시 |
|------|---------------|------|------|
| `작업 이름` | 작업 이름 | `Pipeline\Pipeline_PipeRun` 형식 | `03-BFW-2001\03-BFW-2001_Recovery...` |
| `동기화 ID` | 동기화 ID | 순차 번호 (1~378) | `1` |
| `작업 유형` | 작업 유형 | 한글 유형 | `구성` |
| `계획된 시작 날짜` | 계획된 시작 | yyyy-MM-dd | `2026-03-24` |
| `계획된 끝 날짜` | 계획된 끝 | yyyy-MM-dd | `2026-03-27` |

### 작업 이름 계층 구조

`작업 이름` 컬럼의 백슬래시(`\`)는 TimeLiner에서 계층 구조를 생성합니다:

```
03-BFW-2001\03-BFW-2001_Recovery Stage 2-6-X-0002-1C0031
├── Parent Task: "03-BFW-2001" (Pipeline)
└── Child Task: "03-BFW-2001_Recovery Stage 2-6-X-0002-1C0031" (PipeRun)
    └── = Selection Set 이름과 일치 → "작업 자동 추가" 시 3D 객체 자동 연결
```

### 시간 매핑 전략

| 설정 | 값 |
|------|-----|
| 전략 | Hybrid |
| 기본 시간 | 8시간 |
| 객체당 추가 | 0.5시간 |
| 근무시간/일 | 8시간 |
| 계산식 | `duration = 8h + ObjectCount x 0.5h` |

---

## 3개 파일 간 관계

```
AllProperties CSV (12,009 objects, 136 columns)
  │
  ├──[정제]──→ Refined XLSX (12,009 objects, 66 columns + 4 summary sheets)
  │              ├── Pivot: 정제된 속성 (접두사 제거, Class 분류)
  │              ├── Pipeline_Summary: 147 Pipelines 요약
  │              ├── Class_Distribution: 6개 분류 분포
  │              ├── Equipment_Summary: 110개 장비 요약
  │              └── PipeRun_Detail: 334 PipeRuns 상세
  │
  └──[스케줄]──→ Pipeline Schedule CSV (378 tasks, 5 columns)
                   ├── Pipeline/PipeRun 그룹핑
                   ├── 시간 자동 매핑 (Hybrid)
                   └── TimeLiner Import → 4D 시뮬레이션
```

### 공통 키 필드

| 필드 | AllProperties CSV | Refined XLSX | Pipeline Schedule CSV |
|------|:---:|:---:|:---:|
| ObjectId (GUID) | `ObjectId` | `ObjectId(GUID)` | - |
| Pipeline | `SmartPlant 3D\|Pipeline` | `Pipeline` | `작업 이름` (Parent) |
| PipeRun | `SmartPlant 3D\|PipeRun` | `PipeRun` | `작업 이름` (Child) |
| Level | `Level` | `Level` | - |

---

## 온톨로지 설계를 위한 핵심 관찰

### 1. 객체 분류 체계

모델의 객체는 6개 Class로 분류되며, **Structure(49%)와 Piping(33%)이 전체의 83%**를 차지합니다.
배관 객체만 Pipeline/PipeRun 속성을 가지며, 이것이 4D 스케줄의 기준이 됩니다.

### 2. 속성 밀도 차이

- **공통 속성** (60%+): Name, Status, Date Created/Modified, System Path, SP3d Moniker
- **배관 전용** (24%): Pipeline, PipeRun, NPD, Flow Direction, Spool, Commodity Code
- **희소 속성** (5~10%): Spec Name, BOM description, Support Assembly

### 3. 계층 구조

10단계(L0~L9) 계층에서 **L6~L8에 90%의 객체**가 집중됩니다.
L7이 개별 부품(Geometry Group) 수준으로 가장 의미 있는 데이터를 포함합니다.

### 4. 관계 구조

- **소속 관계**: Object → PipeRun → Pipeline (has-part)
- **공간 관계**: Location, System Path (spatial-containment)
- **자재 관계**: Material, Specification (material-of)
- **시공 관계**: Construction Type, Schedule (planned-construction)

### 5. DisplayString 접두사

AllProperties CSV의 값에는 `DisplayString:` 접두사가 붙어 있습니다.
Refined XLSX에서는 이미 제거되어 있으므로, 온톨로지 구축 시 **Refined XLSX 사용을 권장**합니다.
