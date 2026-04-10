# Phase 1a — Data Realignment Design

> **목적**: Phase 1a(데이터 정제)를 시작하기 전에, 5개의 구조적 결정을 두 단계에 걸쳐 논의한 기록.
> 이 문서는 단순한 task log가 아니라 **downstream 전 단계에 영향을 미치는 설계 결정의 근거**를 남기기 위한 문서이다.
>
> **작성 배경**: 원천 데이터의 분류가 여러 곳에서 모순과 누락을 보이고, Phase 2(온톨로지) 이후의 모든 단계가 Phase 1a의 결과에 의존하므로, "데이터를 처음부터 재정렬"하기로 결정함. 결정 전에 사고 프레임워크 자체를 먼저 확정한다.

---

## 1. 최종적으로 구축하려는 것

### 1.1 전체 파이프라인

```
[BIM Data]
   ↓
[Ingestion]          ← Phase 1 (지금 여기)
   ↓
[Ontology / KG]      ← Phase 2
   ↓
[Quality / Reasoning] ← Phase 3
   ↓
[Analytics]          ← Phase 4 (Phase 2-3과 병렬)
   ↓
[LLM Service]        ← Phase 5
   ↓
[API / UI]           ← Phase 6, 7
```

**목표**: SP3D 기반 플랜트 BIM 모델(12,009 객체, 110K 공간 관계)을 정제된 온톨로지 기반 지식 그래프로 변환하여, 자연어 질의·품질 검증·시공 분석·시각화가 가능한 파이프라인을 Python 단일 저장소로 구축한다.

**데이터 원본**: `data/raw/dxtnavis/2026-04-07/` 단일 스냅샷 (DXTnavis v1.4.0, 12,009 객체)

### 1.2 Phase 1a의 역할

Phase 1a는 원천 데이터의 **클래스 오분류·누락·노이즈를 정리**하여 Phase 2 온톨로지 매핑에 투입할 수 있는 깨끗한 `bim_objects` 테이블을 만드는 단계다.

**결정적 중요성**: 여기서 내리는 분류 결정이 다음 모든 단계의 입력이 된다.
- Phase 2 OWL 클래스 계층 → Phase 1a의 `refined_class` 값이 그대로 OWL 클래스로 변환됨
- Phase 3 SHACL 검증 규칙 → 클래스별 제약을 걸기 때문에 Phase 1a 분류가 틀리면 오탐/누탐 발생
- Phase 4 그래프 분석 → Container/AnalysisVolume 제외 여부가 degree centrality 등을 완전히 바꿈
- Phase 5 LLM 질의 → "피라니 컴포넌트 개수" 같은 질문에 대한 답의 신뢰성
- Phase 6/7 API/UI → 필터, 검색, 카운트의 정확성

따라서 **Phase 1a는 "빠르게 구현"하는 단계가 아니라 "원칙을 먼저 합의하고 그 원칙대로 기계적으로 구현"하는 단계**여야 한다.

### 1.3 Phase 1a의 대상 데이터

- **12,009 객체** (고유 Object GUID)
- **110,173 공간 관계** (adjacency.csv — producer 기반)
- **3,355 연결 그룹** (connected_groups.csv)
- **136 원본 속성** (AllProperties_20260407_184650.csv)
- **기하 정보** (geometry.csv — BBox, centroid, mesh 카운트)
- **검증 정보** (validation.csv — MeshQuality, Verdict, AdjacencyCount 등)

### 1.4 baseline-insights.md 의 기존 9개 인사이트

이전 C# 백엔드 기반 분석에서 아래 인사이트가 정리되어 있었다:

1. "Other" 클래스가 병목 (49.3%) — Container/Uncategorized 분할 권고
2. 백엔드 AABB 분류가 Producer mesh보다 부정확 (precision 35.4%)
3. Giant connected component 1개 + 3,353 singleton containers
4. Hierarchy level이 class의 강한 신호
5. Pipeline이 Class보다 실제 스케줄 축
6. 백엔드 파싱 버그: SourceFileName 0.008%, EquipmentName 153건 누락
7. 이름 패턴이 raw category보다 나은 분류자
8. "Obstruction Volume"이 degree 5,267 허브 (그래프 오염)
9. Mesh quality에 clean size signature

Phase 1a는 이 인사이트들을 **재검증하면서 구현**해야 한다. 단, 인사이트는 2026-03-23 스냅샷 기반일 수 있으므로, 2026-04-07 데이터에서 같은 결론이 나오는지 실증해야 한다.

---

## 2. 구축하기 위해 제기된 5개의 구조적 질문

Phase 1a를 시작하기 전에 아래 5가지 결정이 필요하다. 이 결정들은 서로 독립적이지 않고, downstream Phase 2-7에 연쇄적으로 영향을 미친다.

### Q1. Container 정의 범위 — 무엇을 Container로 부를 것인가?

Other 클래스(5,917)를 분석한 결과 3개 하위 집단이 드러났다:

| Pop | 정의 | 개수 | 실체 |
|----|------|----:|------|
| **A** | HasRealMesh=False AND AdjacencyCount=0 | **3,200** | 순수 행정 컨테이너 (skipped_container) |
| **B** | HasRealMesh=False AND AdjacencyCount>0 | **660** | 계층 컨테이너 (L1~L5, box_placeholder) |
| **C** | HasRealMesh=True | **2,057** | 진짜 물리 객체 (분류 오류 있음) |

**질문**: Container 클래스에 어디까지 포함할 것인가?

- Option A (엄격): Pop A만 → 3,200
- Option B (관용): Pop A + Pop B → 3,860
- Option C (최대): Pop A + Pop B + 고립 Piping 153 → 4,013

### Q2. Pop C(2,057) 재분류 전략 — 백엔드를 바로잡을 것인가?

Pop C(real mesh + 분류 오류)를 분석한 결과 81.7%가 이름 패턴으로 재분류 가능하다:

| 재분류 | 개수 | 패턴 |
|--------|----:|------|
| Structural | 873 | Beam_, Column_, Slab, MemberPart, RectFtg, ... |
| Electrical | 362 | Cableway, Duct Banks, Cable Tray, Conduit |
| HVAC | 38 | Duct, Damper, Diffuser |
| AnalysisVolume | 145 | Insulation Volume |
| Generic (Geometry) | 145 | Geometry |
| Unmatched | 494 | RectFootingPier, Brace, CT, LeftWall, ... (패턴 보강 여지) |

**질문**: 원천 백엔드의 분류를 우리가 override 해도 되는가? 된다면 얼마나?

- Option A (보수): 재분류 없음
- Option B (명시적 패턴만): 1,900건 재분류
- Option C (공격적): Level + 이름 + SystemPath 다중 신호

### Q3. Insulation Volume 처리 — 새 클래스를 만들 것인가?

Pop C 안에 `Insulation Volume` 145건이 있다. 물리 객체처럼 mesh를 가지지만 실제로는 보온재 해석용 아티팩트이다. adjacency에도 참여(총 2,672 edges).

**질문**: 이것을 어떻게 분류할 것인가?

- Option A: 별도 `AnalysisVolume` 클래스 + `exclude_from_graph` 플래그
- Option B: Container로 병합
- Option C: 완전 삭제 (노출 안 함)

### Q4. 고립 Piping 153건 처리 — 클래스와 상태를 분리할 것인가?

Piping 클래스 중 153건이 MeshQuality=`skipped_container`, AdjacencyCount=0, Level=7~8이다. 이름은 Pipe/Flange/Tee/Weldolet 등 실제 배관 부품명을 가진다.

**질문**: 이들의 `object_class`를 어떻게 기록할 것인가?

- Option A: `object_class='Piping'` 유지 + `has_geometry=False` 플래그
- Option B: `object_class='Container'`로 이동

### Q5. 원본 클래스 보존 — Lineage를 얼마나 깊이 기록할 것인가?

재분류 후 원본 백엔드 분류값을 어떻게 다룰 것인가?

- Option A: 덮어쓰기, 원본 버림
- Option B: `original_class` + `refined_class` 두 컬럼 병존

---

## 3. 첫 번째 제안된 흐름 (초기 분석)

### 3.1 Q1 — Container 정의 범위

| Option | 판단을 이끄는 인사이트 | 사고방식 |
|--------|----------------------|----------|
| **A (엄격)** | "원천 시스템의 명시적 신호만 믿는다" | Source-of-truth fundamentalist. MeshQuality=skipped_container는 SP3D가 명시적으로 선언한 것. 추론을 덧붙이는 순간 책임 소재가 모호. |
| **B (관용)** | "컨테이너는 의미적 개념이지 기술적 플래그가 아니다" | Semantic modeler. 실제 기하가 없으면 물리 객체가 아님. box_placeholder는 SP3D가 계층 그룹에 BBox를 씌운 것일 뿐. |
| **C (최대)** | "토폴로지가 현실이다" | Graph theorist. 공간 관계 그래프에 존재감이 없으면(고립) 사실상 컨테이너. |

**초기 권고**: **B (관용)**

- 이유: downstream 엔지니어는 "그래프에 나오는 노드는 진짜 객체여야 한다"는 기대를 가짐
- A는 방어적 쿼리를 매번 필요로 함
- C는 정의가 순환적 ("고립이면 컨테이너, 컨테이너니까 그래프 제외")

### 3.2 Q2 — Pop C 재분류 전략

| Option | 판단을 이끄는 인사이트 | 사고방식 |
|--------|----------------------|----------|
| **A (보수)** | "나의 역할은 보고지, 해석이 아니다" | Compliance-driven. 백엔드가 Other라고 하면 Other다. 가치 창출 없음. |
| **B (명시적 패턴)** | "규칙이 재현 가능하면 그건 해석이 아니라 기계적 변환이다" | Rule-based transformer. 단위 테스트로 고정. 감사 가능. |
| **C (공격적)** | "여러 약한 신호의 결합은 강한 증거다" | Multi-signal classifier. 강력하지만 복잡도 증가. |

**초기 권고**: **B + 잔여분만 C**

- 단순 패턴으로 캡처되는 건 B로 깨끗하게
- 애매한 ~200개만 다중 신호로 재분류
- 설명 가능성 > 정확도

### 3.3 Q3 — Insulation Volume 처리

| Option | 판단을 이끄는 인사이트 | 사고방식 |
|--------|----------------------|----------|
| **A (별도 클래스 + flag)** | "다른 개념은 다른 이름을 가져야 한다" | Taxonomist. 미래 Fireproofing/Acoustic Volume 확장 가능. |
| **B (Container 병합)** | "사용자가 쓰지 않는 구분은 노이즈다" | Pragmatist. 단순함. 정보 손실. |
| **C (완전 삭제)** | "보이지 않는 것이 가장 깨끗하다" | Curator. 1:1 preservation 위반. |

**초기 권고**: **A**

- 가장 보수적이면서 확장성 있음
- 데이터 매니지먼트 원칙: *"Filter by flag, never by deletion"*
- 12,009 count preservation 유지

### 3.4 Q4 — 고립 Piping 153 처리

| Option | 판단을 이끄는 인사이트 | 사고방식 |
|--------|----------------------|----------|
| **A (Piping 유지 + flag)** | "클래스는 정체성, 상태는 별도 컬럼이다" | Schema-first. |
| **B (Container로 이동)** | "행동이 없으면 정체성도 없다" | Behavior-driven. |

**초기 권고**: **A**

- 원칙: *"Class = nature, Flag = condition"*
- "이 모델에 배관이 몇 개인가?" → 2,926 답할 수 있어야 함
- 다음 스냅샷에서 mesh가 수정되면 자동으로 회복 가능

### 3.5 Q5 — 원본 클래스 보존

| Option | 판단을 이끄는 인사이트 | 사고방식 |
|--------|----------------------|----------|
| **A (버림)** | "사용자는 최종 결과만 보면 된다" | UX-first. |
| **B (병존)** | "모든 변환은 추적 가능해야 한다" | Lineage-first. |

**초기 권고**: **B**

- 감사 추적은 비용이 거의 0인데 가치는 무한
- 백엔드 분류 품질을 시계열로 모니터링 가능
- 이해관계자 협상 시 원본 제시 가능

### 3.6 종합 권고 (1차)

| Q | 추천 | 기저 원칙 |
|---|------|----------|
| Q1 | **B** | 물리 객체와 행정 단위를 의미적으로 분리 |
| Q2 | **B + 잔여분 C** | 설명 가능한 규칙 > 블랙박스 heuristic |
| Q3 | **A** | 정보 손실 없는 분류 확장 |
| Q4 | **A** | Class는 정체성, Flag는 상태 |
| Q5 | **B** | Lineage는 비용 0, 가치는 무한 |

### 3.7 공통 관통 원칙 (1차)

1. **Filter, don't delete**: 모든 변환은 원본 옆에 추가, 삭제 금지
2. **Explain before transform**: 재분류 규칙은 단위 테스트 가능한 코드로만
3. **Class vs State separation**: 정체성과 상태를 다른 컬럼으로
4. **Count preservation**: 12,009는 모든 단계에서 유지
5. **Audit trail is non-negotiable**: 원본은 항상 접근 가능

---

## 4. 한 단계 더 깊은 논의

초기 권고에는 각 답변이 **암묵적으로 가정하고 있던 전제**가 있다. 그 전제를 드러내야 한 단계 더 깊은 판단이 가능하다.

### 4.1 Q1 심화 — "컨테이너란 무엇인가?"의 존재론적 역설

**이전 답변의 숨은 전제**:
> "물리 객체 = 만질 수 있는 것, 컨테이너 = 논리적 그룹"

이 전제는 기하(geometry)를 클래스 정의의 기준으로 삼는다. 그런데 여기서 모순이 드러난다.

**한 단계 깊은 질문**: `PipeRun`은 컨테이너인가 아닌가?

- PipeRun은 개념적으로 "Pipe들의 집합" — 논리적 그룹
- 자체 mesh는 없고, 자식 Pipe의 집합 BBox만 가짐
- 그런데 우리는 이걸 `Piping` 클래스로 분류함 (Pipeline/PipeRun 속성 때문)
- 660개 box_placeholder의 `B01-PipingSys-Process`도 똑같이 "Piping 시스템의 그룹"인데 Container로 보내려 함

**두 결정이 일관성이 없다.** 이 모순은 **"Class = nature of the object OR role in hierarchy?"** 라는 질문이다.

| 관점 | 일관된 결정 |
|------|------------|
| Nature 중심 (physical) | PipeRun도 Container로 → Piping 절반이 Container가 됨 → 사용자 혼란 |
| Role 중심 (hierarchical) | box_placeholder도 원래 클래스 유지 → Structure 컨테이너는 Structure, Piping 컨테이너는 Piping |
| Hybrid (class + level) | Container는 완전 행정 노드(L1-L2)에만 → 플랜트/영역만 해당 |

**더 날카로운 답**: **Container 클래스 대신 "container-like" 플래그를 도입**하는 것이 더 정직하다.

```sql
bim_objects (
    object_id PK,
    refined_class      -- Piping, Structure, Equipment, ... (원래 의미론)
    hierarchy_role     -- Leaf, Group, SystemGroup, AreaGroup, Plant
    has_own_geometry   -- True/False (자체 mesh)
    graph_participant  -- True/False (분석 그래프 포함 여부)
)
```

효과:
- "모든 Piping 컴포넌트 조회" → `refined_class='Piping'` (PipeRun 포함)
- "실제 배관 부품만" → `refined_class='Piping' AND has_own_geometry=True`
- "그래프 분석용 노드만" → `graph_participant=True`

**Container를 하나의 클래스로 합치면 원래 클래스 정보가 섞인다. 플래그 기반이 더 깨끗하다.**

### 4.2 Q2 심화 — 재분류의 "근거(ground truth)" 문제

**이전 답변의 숨은 전제**:
> "Beam_* 패턴은 100% Structural이다" — 라고 내가 단정했다

**한 단계 깊은 질문**: 내가 무슨 권한으로 그렇게 주장하는가?

- 5분간 샘플을 본 결과이다
- 엔지니어링 taxonomy 문서를 참조한 것도 아니다
- SP3D 공식 스키마를 본 것도 아니다
- 단지 "Beam처럼 보이니까 Structural이겠지" 하는 직감이다

**Reproducible ≠ Correct.** 재현 가능하지만 검증 불가능한 규칙이다.

**실무적 귀결**: 권위 있는 외부 신호를 찾아야 한다. 다행히 우리에게 아직 활용하지 않은 신호가 있다:

**raw_properties_json 안의 구조화된 필드**:
- `SmartPlant 3D|Eqp Type 0` ~ `Eqp Type 3` — SP3D의 공식 장비 taxonomy (4단계)
- `항목|내부 유형` (Internal Type) — Navisworks 내부 유형
- `항목|유형` (Type) — 표시 유형
- `SmartPlant 3D|System Path` — 계층 경로

**더 날카로운 답**: **재분류 규칙에 2개의 신호가 동시에 일치해야 적용**한다.

```python
def reclassify(obj) -> ClassificationResult:
    signals = {
        'name_pattern': match_name_to_class(obj.display_name),     # Beam_* → Structural
        'system_path':  infer_class_from_path(obj.system_path),    # \Structural\ → Structural
        'internal_type': infer_class_from_type(obj.internal_type), # SP3D 내부 신호
        'eqp_type':     obj.eqp_type_0,                            # SP3D taxonomy
    }
    # 2개 이상 일치 시에만 재분류
    consensus = majority_vote(signals)
    if consensus and signals_agreeing(consensus) >= 2:
        return ClassificationResult(
            refined_class=consensus,
            confidence='high',
            signals_used=signals,
        )
    return ClassificationResult(refined_class='Uncategorized', confidence='low')
```

효과:
- 재분류된 모든 객체는 **최소 2개 독립 신호**를 근거로 가짐
- 감사 시 정량적 설명 가능
- 1개 신호만으로는 재분류하지 않고 Uncategorized로 유지 → 정직함

**이것이 진짜 data analyst의 태도이다**: *"나의 판단에 책임지려면, 그 판단이 근거한 신호를 기록해야 한다."*

### 4.3 Q3 심화 — AnalysisVolume은 온톨로지 어디에 위치하는가?

**이전 답변의 숨은 전제**:
> "AnalysisVolume이라는 별도 클래스를 만든다"

이 전제는 Phase 2 OWL 온톨로지의 클래스 계층을 암묵적으로 가정한다. 그런데 우리는 아직 OWL 스키마를 확정하지 않았다.

**한 단계 깊은 질문**: AnalysisVolume은 BIMObject의 자식인가? 아니면 전혀 다른 종류인가?

| 위치 | 의미 |
|------|------|
| `BIMObject > PhysicalObject > AnalysisVolume` | "분석 볼륨도 물리 객체다" — 기하가 있으니 맞지만, 공간 관계 참여가 부적절 |
| `BIMObject > Container > AnalysisVolume` | "일종의 컨테이너다" — 컨테이너 의미가 흐려짐 |
| `BIMObject > AnalysisArtifact > AnalysisVolume` | "분석 산출물이다" — 가장 정확. 미래 확장 가능 |
| `BIMObject ‖ AnalysisArtifact` (sibling) | 완전히 다른 루트 — 공통 identity 없음 |

**실무적 귀결**: 선택은 단순히 이름이 아니라 **SHACL 검증 규칙이 어떻게 작성될지**를 결정한다.

```
[Option 1] AnalysisVolume < PhysicalObject
  → SHACL: "PhysicalObject는 adjacency 그래프에 참여해야 한다"라고 쓸 수 없음
  → 규칙 반전 필요: "AnalysisVolume만 adjacency에 참여하면 안 된다"
  → OWL 추론 복잡

[Option 3] AnalysisArtifact > AnalysisVolume (권장)
  → SHACL: "PhysicalObject는 adjacency 참여 가능, AnalysisArtifact는 불가"
  → positive rule, 단순
  → 미래 확장성
```

**더 날카로운 답**: Phase 2 OWL 스키마의 루트 구조를 지금 확정하는 것과 같다.

```
BIMEntity
├── BIMObject (물리적 실체 또는 컨테이너)
│   ├── PhysicalObject
│   │   ├── PipingComponent
│   │   ├── StructuralMember
│   │   ├── Equipment
│   │   ├── Support
│   │   └── ElectricalComponent
│   └── Container
│       └── HierarchyNode
└── AnalysisArtifact (엔지니어링 분석 산출물)
    └── AnalysisVolume
        ├── InsulationVolume
        ├── FireproofingVolume (미래)
        └── AcousticVolume (미래)
```

**이 결정이 Phase 2 전체 스키마를 결정**하므로, 지금 Phase 1a에서 `refined_class` 값을 'AnalysisVolume'으로 기록해두면 Phase 2에서 그대로 OWL 클래스로 변환된다.

즉 Q3는 단순히 "어떻게 부를까"가 아니라 **"Phase 2의 top-level taxonomy를 지금 선언하는가"** 라는 질문이다.

### 4.4 Q4 심화 — 시그널 충돌 시 누가 이기는가?

**이전 답변의 숨은 전제**:
> "Class는 정체성, Flag는 상태"

이 전제는 깔끔하지만, **여러 시그널이 충돌할 때 어떻게 해결할지** 말하지 않는다.

**한 단계 깊은 질문**: 153개 고립 Piping에 대한 시그널들이 서로 다른 말을 한다.

| Signal | 말하는 바 | Trust level |
|--------|----------|-------------|
| `object_class='Piping'` (backend) | "이건 배관이다" | Medium (종종 틀림) |
| `MeshQuality='skipped_container'` (backend) | "이건 컨테이너다" | Medium |
| `Level=7 or 8` (source) | "이건 리프 노드다 → 실제 부품일 가능성 높음" | High |
| `display_name='Pipe'\|'Flange'\|'Tee'` | "이건 실제 배관 부품이다" | High |
| `AdjacencyCount=0` | "이건 그래프에 고립되어 있다" | High |

**Backend 자체가 자기 모순**: class='Piping'이라면서 동시에 MeshQuality='skipped_container'를 줬다.

**실무적 귀결**: Trust Hierarchy를 만들어야 한다.

```
Level 1 (source facts, 항상 우선):
  - Hierarchy level (structural)
  - Display name (lexical)
  - Bounding box geometry

Level 2 (computed facts, 검증 가능):
  - AdjacencyCount (from adjacency.csv)
  - HasRealMesh (from validation.csv)

Level 3 (backend interpretations, 의심 가능):
  - object_class (C# refining의 classification)
  - MeshQuality (backend의 자체 판단)

Conflict resolution rule:
  - L1 signals override L3
  - L2 signals can override L3 (with logging)
  - L3 signals used only when L1/L2 silent
```

**더 날카로운 답**: 153개 고립 Piping의 정체는 **추측 대신 실제 데이터를 열어봐야 한다**. 이전 추측("껍데기 배관")도 검증 없는 주장이다.

→ Phase 1a를 시작하기 전에 이 153건의 raw_properties_json을 직접 열어서 `SmartPlant 3D|Commodity Code`, `ShortCode`, `Spool` 등을 확인해야 한다. 값이 비어있으면 껍데기, 있으면 import 직전 상태의 실제 부품이다.

### 4.5 Q5 심화 — Lineage의 레이어 수 결정

**이전 답변의 숨은 전제**:
> "original_class + refined_class 두 컬럼이면 충분하다"

이 전제는 단일 변환(transform)을 가정한다. 하지만 실제로는 여러 변환이 누적된다.

**한 단계 깊은 질문**: 3개월 후 재분류 규칙이 바뀌었을 때, 왜 `refined_class`가 변했는지 어떻게 추적하는가?

- 어느 규칙 버전에 의해 분류되었는가?
- 어느 시그널이 근거였는가?
- 언제 재분류되었는가?

두 컬럼으로는 답할 수 없다. Provenance 깊이의 문제이다.

**Provenance의 5단계**:

| 레이어 | 저장 대상 | 비용 | 가치 |
|--------|----------|------|------|
| L1 | Source value (original_class) | 거의 0 | 필수 |
| L2 | Transformed value (refined_class) | 거의 0 | 필수 |
| L3 | Rule name ("pattern_beam", "isolated_no_mesh") | 적음 | 높음 |
| L4 | Rule version ("v1", "v2") | 적음 | 중간 |
| L5 | Full signal trace (JSON blob) | 중간 | 낮음 |

**더 날카로운 답**: **최소 L1-L3, 권장 L1-L4. L5는 과잉.**

구체 스키마:

```sql
CREATE TABLE bim_objects (
    object_id TEXT PRIMARY KEY,
    original_class TEXT,          -- L1: backend의 답
    refined_class TEXT,            -- L2: 우리의 답
    refining_rule TEXT,            -- L3: "pattern_beam_structural"
    refining_rule_version TEXT,    -- L4: "v1"
    refined_at_utc TIMESTAMP,      -- 재분류 시점
    ...
);
```

효과:
- "왜 이번 달에 Structural이 800개 늘었나요?" → `SELECT refining_rule, COUNT(*) FROM bim_objects WHERE refined_at_utc > ? GROUP BY refining_rule`
- 규칙 버그 발견 시 특정 rule_version 행만 재분류 가능
- A/B 테스트 가능

**Phase 1c(SQLite 확장) 스키마 설계에 직접 반영해야 한다.**

### 4.6 5개 질문을 관통하는 메타 질문

한 단계 더 깊이 보면, 이 5개 질문은 모두 하나의 메타 질문을 묻고 있다:

> **"데이터 분석가는 원천 데이터에 얼마나 개입할 권한이 있는가?"**

| Q | 개입 종류 | 정당화 근거 |
|---|---------|------------|
| Q1 | 클래스 재정의 | 원천의 의미론적 모순 해결 |
| Q2 | 클래스 재분류 | 원천이 놓친 패턴 포착 |
| Q3 | 새 클래스 창조 | 원천에 없는 분류 도입 |
| Q4 | 신호 신뢰도 차등 | 원천의 자기 모순 심판 |
| Q5 | 변환 이력 추적 | 개입의 책임 있는 기록 |

**data analyst의 직업 윤리**: *개입할 수 있다. 하지만 매 개입마다 **근거 + 추적 + 회복 가능성**을 보장해야 한다.*

### 4.7 심화 논의에서 변경된 결론 요약

| Q | 1차 권고 | 심화 권고 | 변화 이유 |
|---|---------|----------|----------|
| Q1 | Container 클래스 (Option B) | **Container 플래그** (refined_class 유지 + hierarchy_role + graph_participant) | PipeRun과 box_placeholder 컨테이너가 일관성 없이 분류되는 모순 발견 |
| Q2 | 명시적 패턴 B | **2-signal consensus** (이름 + system_path/eqp_type) | 단일 패턴은 재현 가능하지만 검증 불가능 |
| Q3 | 별도 AnalysisVolume 클래스 | **동일 (단, BIMObject와 sibling으로 배치)** | Phase 2 OWL 계층 최상위 구조까지 결정 |
| Q4 | Piping 유지 + flag | **동일 (단, raw_properties_json 직접 확인 후 최종 결정)** | 153건 정체를 추측하지 말고 실증 |
| Q5 | 2컬럼 (original + refined) | **4컬럼** (original_class, refined_class, refining_rule, refining_rule_version) | 규칙 변화에 따른 추적 필요 |

---

## 5. 다음 단계 — 결정 전에 실행할 실증 진단

심화 논의 결과, **아직 확정할 수 없는 결정**이 2개 남았다. 추가 데이터 확인이 필요하다.

### 5.1 진단 A — SP3D 구조화 신호의 분포

**목적**: Q2의 2-signal consensus 전략이 실제로 견고한지 사전 검증.

**확인할 것**:
- `raw_properties_json` 안의 `SmartPlant 3D|Eqp Type 0~3` 필드 분포
- `항목|내부 유형`(Internal Type) 필드 분포
- `SmartPlant 3D|System Path` 경로 토큰 분포
- 각 신호별로 클래스와의 상관관계 (Structural/Electrical/HVAC 등)
- 이름 패턴과 구조화 신호의 합의 비율

**기대 결과**:
- 이름 패턴 873 Structural 중 몇 %가 system_path에도 \Structural\ 포함?
- Eqp Type 0이 있는 660 Equipment 중 몇 %가 taxonomy와 일치?

### 5.2 진단 B — 153 고립 Piping의 실체

**목적**: Q4의 최종 결정 근거.

**확인할 것**:
- 153건의 `SmartPlant 3D|Commodity Code` 값 존재 여부
- `ShortCode`, `Spool`, `Stress System No` 값
- `Pipeline`, `PipeRun` 필드 값
- 원본 백엔드 refining에서 `SourceFileName`, `SourceFilePath`

**기대 결과**:
- 값이 있으면 → 진짜 배관 부품, MeshQuality가 잘못됨 (Piping 유지 + 플래그)
- 값이 없으면 → 껍데기, 실제 container처럼 동작 (플래그로 격리)

### 5.3 결정 흐름

```
진단 A 실행
  ├─ Eqp Type + SystemPath의 classification power 확인
  └─ 2-signal consensus의 coverage 계산

진단 B 실행
  ├─ 153건의 상업 코드/스풀/부품 정보 확인
  └─ "진짜 부품 vs 껍데기" 비율 결정

결정 확정
  ├─ Q1: Container 플래그 스키마 확정
  ├─ Q2: 2-signal consensus 규칙 코드화
  ├─ Q3: Phase 2 OWL 루트 구조 선언
  ├─ Q4: 153건 처리 방침 결정
  └─ Q5: 4컬럼 lineage 스키마 확정

Phase 1a 코드 구현 시작
  ├─ src/bimkg/ingest/clean.py
  ├─ src/bimkg/ingest/classifier.py (신규)
  ├─ src/bimkg/ingest/lineage.py (신규)
  └─ tests/test_ingest/test_clean.py
```

---

## 6. 이 문서의 역할

- **Phase 1a 코드 구현 시 참조**: 왜 이렇게 구현했는지의 근거
- **Phase 2 OWL 스키마 설계 시 참조**: top-level taxonomy의 최초 선언
- **코드 리뷰 시 참조**: 재분류 규칙이 원칙과 일치하는지 검증
- **미래의 재분류 규칙 변경 시 참조**: 기존 원칙을 깨지 않고 확장하는지 확인

이 문서는 **Phase 1a 완료 후에도 유효**하며, Phase 2-7 내내 ontology 설계 의사결정의 근거로 사용된다.
