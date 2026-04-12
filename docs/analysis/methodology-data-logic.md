# 데이터 논리 체인 — 원본에서 시공계획까지

> 이 프로젝트에서 사용한 **모든 데이터**, **적용한 판정 기준**, **분석 논리**, **도출된 결과**를
> 하나의 문서에서 추적할 수 있도록 정리합니다.

---

## 전체 흐름도

```
┌─────────────────────────────────────────────────────────┐
│  1. 원본 데이터 (DXTnavis, 11 files)                     │
│     ├── XLSX: Class, DisplayName, SystemPath, 속성 136개 │
│     ├── AllProperties CSV: SP3D 원본 속성                │
│     ├── adjacency.csv: 110K 공간 관계                    │
│     ├── geometry.csv: BBox, centroid, mesh 메타           │
│     ├── validation.csv: 메시 품질                        │
│     └── connected_groups.csv: 3,355 그룹                 │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  2. 정제 + 파생 (Phase 1a~1e)                            │
│     ├── 분류: 3-tier classifier → refined_class          │
│     ├── 단위 변환: SP3D 문자열 → SI (kg, m, kPa, °C)    │
│     ├── 플래그: is_container, is_analysis_volume 등      │
│     ├── 신뢰도: classification_confidence 3단계          │
│     └── 결합: 5개 원본 → 218컬럼 Gold 테이블             │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  3. 온톨로지 (Phase 2)                                   │
│     ├── OWL 타이핑: refined_class + 플래그 → 28개 클래스 │
│     ├── 공유 개체: Pipeline 147, PipeRun 334 등          │
│     └── 공간 관계: adjacency → adjacentTo 트리플         │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  4. 분석 (Phase 4)                                       │
│     ├── 인접 등급: overlap/touch/neartouch → 3 tier      │
│     ├── 시공 존: Louvain community → 29 zones            │
│     ├── 시공 순서: 3종 제약 → precedence DAG             │
│     └── Critical path: DAG 최장 경로 → 53 steps         │
└─────────────────────────────────────────────────────────┘
```

---

## 1. 원본 데이터와 특성

### 1.1 출처

| 파일 | 생성자 | 내용 | 크기 |
|------|--------|------|------|
| `Refining_ObjectID_20260412_064240.xlsx` | DXTnavis v1.4.0 (PR #3) | 12,009 objects × 135 cols, Class 분류 포함 | 5 MB |
| `AllProperties_20260407_184650.csv` | DXTnavis v1.4.0 | 12,009 × 136 SP3D 원본 속성 | 42 MB |
| `adjacency.csv` | DXTnavis | 110,173 producer 공간 관계 | 10 MB |
| `geometry.csv` | DXTnavis | BBox min/max, centroid, mesh 정보 | 4 MB |
| `validation.csv` | DXTnavis | 메시 품질 verdict, GroupId | 1 MB |
| `connected_groups.csv` | DXTnavis | 3,355 연결 그룹 | 0.3 MB |

### 1.2 원본의 한계 (알고 사용한 것)

| ID | 한계 | 영향 | 대응 |
|----|------|------|------|
| K1 | validation.csv ParentId 불완전 (294/12,009) | 계층 정보 결손 | AllProperties.csv 에서 대체 |
| K2 | Equipment Eqp Type 0 커버리지 20% (153/770) | 세부 분류 불가 | UnclassifiedEquipment 서브클래스 |
| K3 | Pipeline 147 vs XLSX 157 차이 | FindKey 로직 한계 | 147 기준으로 진행 |

### 1.3 원본이 제공하는 직접 정보

| 정보 | 원본 | 커버리지 | 의미 |
|------|------|:--------:|------|
| 객체 좌표 | geometry.csv → centroid_x/y/z | 12,009/12,009 (100%) | 3D 공간 위치 |
| 바운딩 박스 | geometry.csv → bbox_min/max | 12,009/12,009 (100%) | 객체 크기 |
| 메시 품질 | validation.csv → verdict | 12,009/12,009 (100%) | 렌더링 가능 여부 |
| SP3D 속성 문자열 | AllProperties CSV | 가변 (col별 0.3%~100%) | 엔지니어링 원본 |
| 공간 인접 | adjacency.csv | 110,173 pairs | AABB 기반 근접 |
| 연결 그룹 | connected_groups.csv | 12,009/12,009 | 연결 컴포넌트 소속 |
| 분류 라벨 | XLSX Class 컬럼 | 12,009/12,009 | C# InferClass 출력 |

---

## 2. 분류 논리 (refined_class)

### 2.1 판정 기준: C# InferClass 3-tier

DXTnavis 의 `RefinedXlsxExporter.InferClass` 가 적용하는 3단계 분류:

```
Tier 1: 명시적 Class 속성
  "항목|Class", "SmartPlant 3D|ClassDisplayName" 등에 값이 있으면 그대로 사용.
  → 대부분의 객체가 여기서 분류됨.

Tier 2: 속성 키 이름 추론
  속성 키에 "Pipeline", "PipeRun", "Equipment Name" 등이 있으면 해당 클래스.
  → Piping 이 Structure 보다 우선.

Tier 3: 키워드 regex 매칭 (PR #3 이후)
  combined = (system_path + display_name + 속성 키).lower()
  순서: Piping → Equipment → Structure → Electrical → HVAC → Instrumentation → Other
  
  Piping regex: \b(pipe(?!\s+(rack|trench|support|way|bridge|shoe))|valve|flange|...)\b
  → "pipe" 뒤에 구조물 명사가 오면 거부 (negative lookahead)
  → 나머지 키워드는 단어 경계(\b) 매칭
```

### 2.2 Python 포트와 Oracle 계약

| 항목 | 설명 |
|------|------|
| **구현** | `src/bimkg/ingest/xlsx_classifier.py` |
| **검증** | `test_oracle_100_percent_agreement`: 12,009/12,009 = 100% 일치 |
| **의미** | Python 분류기가 C# 과 동일한 결과를 내므로, XLSX 의 Class 컬럼을 재현 가능 |

### 2.3 이 분류가 사용된 곳

| 다운스트림 | 사용 방식 |
|-----------|----------|
| Gold `refined_class` | 전체 파이프라인의 기본 분류 축 |
| OWL rdf:type | PhysicalObject 서브클래스 결정 (PipingComponent, StructuralMember 등) |
| Foundry Object Type | piping.parquet, structural.parquet 등 파일 분할 |
| PowerBI dim_class | 클래스별 집계 |
| 시공 존 분석 | 존 내 클래스 구성 비교 |
| 시공 순서 | class_order 제약 (Equipment → Structure → Piping → Electrical → HVAC) |

### 2.4 발견된 문제와 해결

**M1 Finding**: C# 의 substring 매칭이 "Pipe Rack" 을 Piping 으로 오분류 (997건).
- **해결**: DXTnavis PR #3 의 negative lookahead regex 를 Python 에 동일 적용
- **결과**: Piping 4,014 → 3,062 (-952), 2026-04-12 snapshot 으로 재정렬
- **잔여**: LIKELY_BUG 136건 (대부분 Tier 2 통과 후 metadata 없는 legit fitting)

---

## 3. 물리량 추출 (단위 변환)

### 3.1 판정 기준

SP3D 속성은 문자열로 저장됨. 예: `"17 ft  1.48 in"`, `"0 lbm"`, `"150 # (RF)"`.

| 원본 형태 | 파싱 규칙 | 결과 | 커버리지 |
|-----------|----------|------|:--------:|
| `"17 ft 1.48 in"` | imperial → metric | 5.2248 m | |
| `"1234.5 kg"` | 직접 추출 | 1234.5 kg | |
| `"0 lbm"` | lbm → kg (× 0.4536) | 0.0 kg | |
| 빈 값 / NaN | → NaN (null) | null | |

### 3.2 변환된 컬럼

| 원본 컬럼 (SP3D 문자열) | 변환 컬럼 (SI float64) | 커버리지 |
|------------------------|----------------------|:--------:|
| sp3d_dry_weight | dry_weight_kg | 5,135 / 12,009 (42.8%) |
| sp3d_wet_weight | wet_weight_kg | 116 / 12,009 (1.0%) |
| sp3d_length | length_m | 1,690 / 12,009 (14.1%) |
| sp3d_design_max_pressure | design_pressure_kpa | 2,356 / 12,009 (19.6%) |
| sp3d_design_max_temperature | design_temperature_c | 2,356 / 12,009 (19.6%) |

### 3.3 이 물리량이 사용된 곳

| 다운스트림 | 사용 방식 |
|-----------|----------|
| OWL data property | `bim:dryWeightKg`, `bim:lengthM` 등 (xsd:double) |
| 양중 분석 | 무거운 객체 위치 식별, 존 별 총 중량 |
| PowerBI fact_objects | weight/length/pressure 집계 |

---

## 4. 플래그 파생

### 4.1 각 플래그의 판정 기준

| 플래그 | 판정 기준 | True 개수 | 원본 근거 |
|--------|----------|----------:|----------|
| `is_container` | validation.csv verdict = "skipped_container" AND adjacency_count = 0 | 3,353 | validation.csv |
| `is_analysis_volume` | display_name 에 "Insulation Volume" 또는 "Volume" 패�� | 145 | XLSX display_name |
| `has_real_mesh` | vertex_count > 0 AND triangle_count > 0 | 8,656 | geometry.csv |
| `is_parent_box` | **has_real_mesh=False AND bbox_volume > 99th pctile (36.3 m³)** (Finding M3) | 448 | geometry.csv |
| `in_giant_group` | connected_groups.csv 에서 가장 큰 그룹 소속 | 8,626 | connected_groups.csv |
| `is_bbox_placeholder` | mesh_quality = "box_placeholder" | 가변 | validation.csv |
| `graph_participant` | NOT (container OR analysis_volume OR parent_box OR bbox_placeholder) | **7,840** | 복합 |

### 4.2 이 플래그가 사용된 곳

| 플래그 | 다운스트림 사용 |
|--------|----------------|
| `is_container` | OWL 타이핑 → HierarchyNode (Container 분기), 물리 객체 분석에서 제외 |
| `is_analysis_volume` | OWL 타이핑 → AnalysisVolume (AnalysisArtifact 분기), 물리 분석에서 제외 |
| `has_real_mesh` | 메시 품질 분석, "빈 메시" 객체 공간 분포 시각화 |
| `is_parent_box` | OWL 타이핑 → HierarchyNode, graph_participant 에서 제외, adjacency 오�� 방지 (M3) |
| `graph_participant` | 모든 그래프 분석의 기본 필터 (Louvain, precedence, Neo4j IN_ZONE) |
| `in_giant_group` | Foundry in_group Link Type, 그래프 연결성 검증 |

### 4.3 플래그의 상호 관계 (M3 ���영)

```
12,009 전체 객체
├── is_analysis_volume = True: 145 (AnalysisVolume)
├── is_container = True: 3,353 (HierarchyNode)
├── is_parent_box = True: 448 (HierarchyNode — M3 발견)
│   └── 271 은 container 가 아닌 parent box (나머지 177 은 container 와 중복)
├── is_bbox_placeholder = True: 223 (refined_class 유지, 그래프 제외)
└── graph_participant = True: 7,840 (PhysicalObject — 분석 대상)
    ├── has_real_mesh = True: 7,840
    └── has_real_mesh = False: 0
```

---

## 5. 분류 신뢰도 (classification_confidence)

### 5.1 판정 기준

Piping 객체에 대해서만 세분화 (비 Piping 은 전부 HIGH):

| 등급 | 조건 | 개수 | 의미 |
|------|------|-----:|------|
| **HIGH** | sp3d_pipeline 있음 AND (commodity_code OR short_code OR spec_name OR npd) 있음 | 2,926 | 진짜 배관 — pipeline 소속 + 메타데이터 확인 |
| **LOW** | pipeline xor metadata 둘 중 하나만 | 0 | (2026-04-12 이후 소멸) |
| **LIKELY_BUG** | 둘 다 없음 | 136 | 오분류 의심 — Tier 2 통과했지만 메타 없음 |

LIKELY_BUG 세부 원인:
- `piping_no_metadata_unknown`: 128 (Tier 2 Pipeline 키 있으나 metadata 없음 — 대부분 legit)
- `piping_no_metadata_pipe_rack_folder`: 8 (Tier 2 로 통과한 잔여)

### 5.2 이 신뢰도가 사용된 곳

| 다운스트림 | 사용 방식 |
|-----------|----------|
| OWL data property | `bim:classificationConfidence` (Q3-C: 타입 분리 대신 annotation) |
| Phase 2 향후 | PipingComponent 중 HIGH 만 신뢰 가능한 부분집합 |
| SPARQL 필터 | `FILTER(?conf = "HIGH")` 로 깨끗한 subset 선택 |

---

## 6. 공간 인접 관계 (adjacency)

### 6.1 원본: AABB 기반 근접 판정

DXTnavis 가 Navisworks API 로 바운딩 박스 간 근접을 계산. **물리적 표면 접촉이 아님.**

| 속성 | 의미 | 범위 |
|------|------|------|
| relation_type | overlap / touch / neartouch | 3 종류 |
| distance_m | 두 BB 간 최단 거리 | 0 ~ 0.193m |
| overlap_volume_m3 | BB 겹침 부피 | 0 ~ 41,150 m³ |
| tolerance_m | 근접 판정 허용 오차 | 0.01 ~ 0.20m (93% 가 0.15m) |

### 6.2 3단계 품질 분류 (Finding M2)

| Tier | 조건 | 간선 수 | 물리적 해석 |
|------|------|--------:|-----------|
| **Strong** | relation_type = "touch" | 13,422 | 표면 맞닿음 → 볼트/용접/플랜지 |
| **Medium** | overlap < 0.01 m³ | 73,222 | 작은 간섭 → 관통부/접합부 |
| **Weak** | overlap > 1 m³ 또는 neartouch | 47,786 | BB 겹침 또는 근접 → 직접 접촉 아님 |

**근거**: max overlap 41,150 m³ = 한 변 34.5m 정육면체. 시스템 그룹 객체 (B01-PipingSys 등) 의 BB 겹침.

### 6.3 Tier 에 따른 precedence 영향 (A/B 테스트)

| 입력 | DAG 간선 | Critical chain | 해석 |
|------|--------:|---------------:|------|
| All (220K) | 41,244 | 88 steps | 과도하게 보수적 — BB 노이즈 포함 |
| Strong only (13K) | 4,588 | 17 steps | 최소 필수 순서 — 물리적 접촉만 |
| **Strong+Medium (87K)** | **18,085** | **53 steps** | **현실적 타협점 — 채택** |

### 6.4 이 인접 정보가 사용된 곳

| 다운스트림 | 사용 방식 | Tier |
|-----------|----------|------|
| OWL `bim:adjacentTo` | 220K 트리플 (전체) | All |
| Precedence DAG `adjacency_interference` | 같은 클래스 인접 → 아래쪽 먼저 | Strong+Medium |
| Louvain zone detection | 커뮤니티 탐지 입력 그래프 | All (물리 객체만) |
| Neo4j ADJACENT_TO | relationType, distanceM, overlapM3 속성 포함 | All + 속성 |
| 존 간 교차 간선 비율 | A/B 테스트 (Grid vs Louvain) 지표 | All |

---

## 7. OWL 타이핑 논리

### 7.1 판정 기준 (우선순위 순)

```
if is_analysis_volume == True → AnalysisVolume
elif is_container == True → HierarchyNode
elif is_parent_box == True → HierarchyNode          ← M3 추가
else:
    refined_class → PhysicalObject 서브클래스 매핑:
        Piping → PipingComponent
        Structure → StructuralMember
        Equipment → (Eqp Type 0 값으로 서브클래스, 없으면 UnclassifiedEquipment)
        Electrical → ElectricalComponent
        HVAC → HvacComponent
        Other → UncategorizedObject
```

### 7.2 결과 분포 (M3 반영)

| OWL 클래스 | 개수 | 결정 근거 |
|-----------|-----:|----------|
| PipingComponent | 2,830 | graph_participant + refined_class=Piping |
| StructuralMember | 2,583 | graph_participant + refined_class=Structure |
| UncategorizedObject | 1,305 | graph_participant + refined_class=Other |
| ElectricalComponent | 867 | graph_participant + refined_class=Electrical |
| Equipment 서브클래스 (8종) | 704 | graph_participant + refined_class=Equipment + sp3d_eqp_type_0 |
| **HierarchyNode** | **3,624** | **is_container (3,353) + is_parent_box (271 non-container)** |
| AnalysisVolume | 145 | is_analysis_volume=True |
| HvacComponent | 65 | graph_participant + refined_class=HVAC |
| 기타 (bbox_placeholder 등) | 486 | refined_class 유지, graph_participant=False |
| **계** | **12,009** | |

### 7.3 공유 개체 (Named Individuals)

| 클래스 | 개수 | 원본 근거 | 사용 |
|--------|-----:|----------|------|
| Pipeline | 147 | sp3d_pipeline 고유값 | belongsToPipeline 링크 대상 |
| PipeRun | 334 | sp3d_pipe_run 고유값 | belongsToPipeRun 링크 대상 |
| Level | 10 | level 0~9 | atLevel 링크 대상 |
| Material | 4 | sp3d_material 고유값 | hasMaterial 링크 대상 |
| Specification | 10 | sp3d_spec_name 고유값 | hasSpecification 링크 대상 |

---

## 8. 시공 존 (Louvain Community)

### 8.1 입력

| 항목 | M3 이전 | M3 이후 (현재) | 설명 |
|------|-------:|---------------:|------|
| 그래프 노드 | 8,511 | **7,840** | graph_participant=True (parent box + placeholder 제외) |
| 그래프 간선 | 107,604 | **28,825** | clean graph — parent box 의 거대 BB 간선 제거 |
| 최대 degree | 5,161 | **388** | 47m 거대 BB 노드 제거 |
| Components | 1 | **55** | 거대 허브 제거 후 자연 분리 |
| 알고리즘 | Louvain | Louvain | community detection |
| resolution | 3.0 | 3.0 | |
| **존 수** | 29 | **144** | 더 세밀한 시공 존 |

### 8.2 A/B 테스트: Grid vs Louvain (M3 이전 데이터, 역사적 참조)

| 지표 | Grid 15m (90존) | Louvain (17존) | 승자 |
|------|---------------:|---------------:|:----:|
| 교차 간선 비율 | 44.4% | 14.1% | Louvain |
| 존 크기 CV | 1.50 | 0.79 | Louvain |
| 존 내 평균 거리 | 낮음 | 높음 | Grid |
| 파이프라인 분산 | 3.2 존/pipeline | 1.7 존/pipeline | Louvain |

**결정**: Louvain 채택 (3/4 지표 승리). resolution=3.0 유지.

> **참고**: M3 이후 clean graph 에서 Louvain (res=3.0) 은 144 존을 생성. 오염된 데이터에서 29 존이었던 이유는 degree-5,267 허브가 대부분의 노드를 하나의 커뮤니티로 묶었기 때문. 정리 후 자연스럽게 세밀한 존 분할이 됨.

### 8.3 결과 (M3 이후)

```
144 zones, cross-zone edges: 1,754 / 28,578 (6.1%)
55 connected components (거대 허브 제거 후 자연 분리)
```

### 8.4 이 존 정보가 사용된 곳

| 다운스트림 | 사용 방식 |
|-----------|----------|
| Precedence DAG | class_order 와 vertical 제약을 존 내에서만 적용 |
| 존 간 의존성 | MUST_PRECEDE 간선이 존 경계를 넘으면 → ZONE_PRECEDES (108 쌍) |
| Neo4j IN_ZONE | 7,840 간선 (object → zone) |
| 간트 차트 | 존 단위 공정계획 시각화 |
| 공간 시공 파도 | 존 별 install_rank 를 좌표에 매핑 |

---

## 9. 시공 순서 (Precedence DAG)

### 9.1 3종 제약의 논리

| 제약 유형 | 논리 | 간선 수 | 원본 데이터 |
|-----------|------|--------:|-----------|
| **class_order** | 같은 존 안에서 Equipment → Structure → Piping → Electrical → HVAC | 150 | refined_class + zone_id |
| **vertical** | 같은 존 + 같은 클래스 안에서 낮은 고도 먼저 (3m 단위 bin) | 332 | centroid_z + zone_id + refined_class |
| **adjacency_interference** | Strong+Medium 인접 + 같은 클래스 → 아래쪽 먼저 | 17,732 | adjacency tier + refined_class + centroid_z |

### 9.2 DAG 구성 (M3 이후)

- 노드: **7,840** (graph_participant=True)
- 간선: **18,214** (방향, 비순환 보장)
- cycle 이 발생하면 마지막 back-edge 제거로 DAG 유지

### 9.3 Critical Path (M3 이후)

- 길이: **44 steps** (was 53 — parent box 제거로 9 steps 단축)
- 시작: 기초 슬라브
- 구성: 대부분 Structure 의 adjacency_interference (아래→위 진행)
- 의미: "무한한 자원이 있어도 최소 53번의 순차 설치는 건너뛸 수 없다"

### 9.4 존 간 의존성

Precedence 간선이 존 경계를 넘으면 존 간 의존성이 됨:
- 82개 존 쌍에 의존성 존재
- 위상 정렬로 29개 존의 시공 순서 결정
- 가장 무거운 의존성: Zone 0 → Zone 3 (가장 많은 교차 간선)

---

## 10. Neo4j 그래프 DB 표현

### 10.1 노드

| 라벨 | 개수 | 속성 | 원본 |
|------|-----:|------|------|
| BIMObject | 12,009 | objectId, displayName, refinedClass, centroidX/Y/Z, dryWeightKg, confidence, criticalStep | Gold |
| Pipeline | 147 | pipelineId, name | sp3d_pipeline 고유값 |
| Zone | **144** | zoneId, zoneNumber, installRank, objectCount, equipmentCount, totalWeightKg | Louvain 결과 (M3 이후) |

### 10.2 간선 (M3 이후)

| 관계 | 개수 | 속성 | 논리 근거 |
|------|-----:|------|----------|
| ADJACENT_TO | 220,346 | relationType, distanceM, overlapM3 | DXTnavis AABB 근접 (§6) |
| MUST_PRECEDE | **18,214** | edgeType, onCriticalPath | 3종 제약 (§9) — Strong+Medium, clean graph |
| HAS_PARENT | 12,008 | — | XLSX 계층 (parent_id) |
| IN_ZONE | **7,840** | — | Louvain community (§8), graph_participant only |
| BELONGS_TO_PIPELINE | 2,926 | — | sp3d_pipeline 매핑 (§7.3) |
| ZONE_PRECEDES | **108** | dependencies | 존 간 의존성 (§9.4) |

---

## 11. 의사결정 요약

이 프로젝트에서 내린 주요 결정과 그 근거:

| ID | 결정 | 근거 | 검증 방식 |
|----|------|------|----------|
| D1 | Medallion architecture | Foundry 패턴 일치 | 구조적 결정, 비교 불가 |
| D2 | XLSX 를 source-of-truth | 프로젝트 소유자가 DXTnavis 신뢰 | Oracle test 100% |
| D5 | Container/AnalysisVolume = 플래그 | Phase 2 에서 OWL 클래스로 승격 가능 | 상호 배타성 확인 (overlap 0) |
| D10 | OWL sibling 구조 | SHACL positive rule 작성 가능 | 구조적 결정 |
| Q2-C | Equipment 서브클래스 | Eqp Type 0 7값 + Unclassified | 커버리지 20%, 있는 건 의미 있음 |
| Q3-C | Confidence = annotation | PR #3 후 136건은 대부분 legit | LIKELY_BUG 분석으로 확인 |
| Q5-B | Pipeline = Named Individual | SPARQL 즉시 질의 가능 | 147+334 = 481 개체 |
| Q6-C | ABox 관심사별 분할 | spatial 분리 → 독립 재생성 | 파일 크기 비교 |
| M2 | Adjacency 3-tier | max overlap 41K m³ = BB | A/B: 88→17→53 steps |
| **M3** | **is_parent_box 플래그** | **448 meshless+oversized objects = 66% 오염** | **graph 8,511→7,840, degree 5,161→388, zones 29→144, chain 53→44** |
| — | Louvain (res=3.0) | Grid 대비 3/4 지표 승리 | A/B test 4 metrics |
| — | Strong+Medium precedence | 물리 접촉 + 간섭까지 포함 | A/B: 17 vs 53 vs 88 |

---

## 12. 데이터 흐름 추적 테이블

각 최종 산출물이 어떤 원본 → 어떤 논리를 거쳐 도출되었는지:

| 최종 산출물 | 원본 데이터 | 적용 논리 | 참조 섹션 |
|-----------|-----------|----------|----------|
| Gold `refined_class` | XLSX Class | 3-tier classifier + PR #3 regex | §2 |
| Gold `dry_weight_kg` | AllProperties sp3d_dry_weight | unit_parser regex → SI | §3 |
| Gold `is_container` | validation.csv | verdict + adjacency_count 조합 | §4 |
| Gold `is_parent_box` | geometry.csv | has_real_mesh=False + bbox > 99pctile (M3) | §4 |
| Gold `graph_participant` | 복합 플래그 | NOT (container OR AV OR parent_box OR placeholder) | §4 |
| Gold `classification_confidence` | sp3d_pipeline + metadata 컬럼 | pipeline ∩ metadata → HIGH/LOW/BUG | §5 |
| OWL rdf:type | refined_class + 플래그 + eqp_type_0 | 우선순위 분기 | §7 |
| OWL `bim:adjacentTo` | adjacency.csv | 대칭화 (110K → 220K) | §6 |
| Zone assignment | adjacency graph (물리 객체) | Louvain res=3.0 | §8 |
| Precedence DAG | zone + class + z + adjacency tier | 3종 제약 → DAG | §9 |
| Critical path | Precedence DAG | DAG longest path | §9.3 |
| 간트 차트 | zone stats + zone DAG | 위상 정렬 순서 | §9.4 |

---

*이 문서는 프로젝트의 데이터 논리 체인을 추적하기 위한 참조 문서입니다.
새로운 데이터나 분석이 추가되면 해당 섹션을 갱신합니다.*

*Last updated: 2026-04-13 (M3 parent box contamination 반영)*
