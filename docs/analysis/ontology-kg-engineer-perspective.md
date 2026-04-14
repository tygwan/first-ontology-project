# 온톨로지·지식그래프 엔지니어 관점 — 7가지 역량 총정리

> 이 문서는 BIM Knowledge Graph Pipeline 프로젝트를 **온톨로지/지식그래프
> 엔지니어** 직군 (Saltlux, LG CNS, Samsung SDS, KT, Stardog, Ontotext 등)
> 의 채용 관점에서 재해석한 자료입니다. 단순히 "뭘 만들었는가" 가 아니라
> **"이 산출물이 어떤 실무 역량을 증명하는가"** 를 7가지 축으로 정리하고,
> 각 역량마다 면접에서 사용할 수 있는 **언어** 와 코드/문서 출처를 명시합니다.
>
> 작성 기준 스냅샷: `2026-04-12`
> 코드 경로는 모두 `/home/taegwan-dev/dev/first-ontology-project` 기준

---

## 0. 한눈에 보기

| # | 역량 축 | 핵심 증명 산출물 | 채용 시장에서의 가치 |
|:-:|---------|------------------|---------------------|
| 1 | 도메인 온톨로지 직접 설계 | 28 OWL classes + R4 결정 기록 D1~D9 | "OWL 사용자" 가 아닌 **"온톨로지 설계자"** |
| 2 | SHACL 기반 품질 게이트 운영 | 6 shapes × 468 위반 자동 탐지 + 피드백 루프 | 단순 검증이 아닌 **정책적 severity 설계** |
| 3 | 다중 질의 계층 통합 | 5-tool ReAct agent (SPARQL/Cypher/SQL/FTS5/KPI) | **GraphRAG / TalkEasy 류 제품 backend pattern** |
| 4 | Medallion + 온톨로지 결합 아키텍처 | Bronze→Silver→Gold→ABox 4-tier | **스키마 진화에 강한 KG 운영** |
| 5 | 데이터 품질 피드백 루프 | M1/M2/M3 + DXTnavis PR #3, Issue #4 | **end-to-end ownership** |
| 6 | OWL 추론 + 공유 URI 전략 | owlrl + 505 공유 개체 + 3 파일 분할 | **대용량 Triple Store 운영 감각** |
| 7 | FastAPI + Pydantic 백엔드 | 12 REST endpoints + Swagger + 336 tests | **KG 를 API 로 추상화** |

**한 줄 결론**: 이 프로젝트는 **mid-level (3-5년차) 온톨로지/KG 엔지니어**
포지션에서 방어 가능한 수준의 실증 자료를 갖췄습니다. senior 수준은
"아직 증명하지 않은 것 (§9)" 의 1-2개를 추가하면 도달.

---

## 1. 도메인 온톨로지를 처음부터 설계한 경험

### 증명 산출물

- `src/bimkg/ontology/schema.py` — 28 OWL classes + 8 object properties + 32 data properties
- `src/bimkg/ontology/namespaces.py` — 도메인 namespace 설계 (`bim:`, `inst:`, `spatial:`)
- `docs/PROJECT-JOURNAL.md §4` — R4 결정 기록 D1~D9 (왜 sibling 인지, 왜 Equipment 만 8 subclass 인지)
- `docs/analysis/phase-1a-data-realignment-design.md` — Q1~Q8 8개 구조적 질문 매트릭스

### 왜 채용 시장에서 중요한가

대부분의 후보자는 "Protégé 로 .owl 파일 만들어봤음" 수준에 머무릅니다. 하지만
온톨로지 회사가 실제로 찾는 사람은 **새 도메인을 보고 클래스 계층을 어떻게
나눌지 trade-off 분석을 할 수 있는 사람** 입니다. 이건 OWL 문법이 아니라
**모델링 의사결정** 능력입니다.

### 이 프로젝트에서 증명한 것

- 최상위 taxonomy 에 3 후보 (단일 트리 / sibling / multi-root) 를 **실제로 비교**
  - 단일 트리: 분석 결과(Louvain zone) 가 PhysicalObject 로 잘못 추론되는 문제
  - sibling (BIMObject ∥ AnalysisArtifact): 분석 아티팩트와 물리 객체를 섞지
    않으면서 공통 속성 `objectId` 와 `label` 만 BIMEntity 에서 공유
  - multi-root: 너무 평평해 구조 활용 어려움
- Q1~Q8 8개 구조적 질문 (예: "Louvain 커뮤니티는 PhysicalObject 인가 분석
  결과인가?", "Pipeline 멤버십은 meronym 인가 association 인가?") 을 만들고
  각 옵션에 대한 답을 매트릭스로 평가
- Equipment 만 8 subclass 세분화 (`ProcessEquipment`, `ElectricalEquipment`,
  `HvacEquipment`, `CivilElements`, `BlackBoxSystems` 등) — 다른 클래스는 flat
  유지로 모델 복잡도 통제
- 공유 개체 (Pipeline 147, PipeRun 334, Level 10, Material 4, Spec 10 = 505개)
  를 Context 분류로 별도 관리 → ABox 파일 크기 최적화 + 재사용성

### 면접 언어

> "BIM 객체 온톨로지를 설계할 때 처음에는 BIMEntity 하나 밑에 분석 결과까지
> 전부 두는 단일 트리 구조를 시도했습니다. 그런데 OWL RL 추론을 돌리니
> Louvain 커뮤니티가 PhysicalObject 로 잘못 추론되는 문제가 생겼습니다.
> sibling 구조 (BIMObject ∥ AnalysisArtifact) 로 전환해서 공통 속성
> objectId 와 label 만 BIMEntity 에서 공유하고 하위는 완전히 분리했고,
> 이 결정 근거를 R4 기록에 D1 으로 남겨서 후속 온톨로지 버전 관리 시
> 되돌아볼 수 있게 만들었습니다."

---

## 2. SHACL 기반 데이터 품질 게이트 운영

### 증명 산출물

- `src/bimkg/validation/shapes.py` — 6 shapes 정의 (179 lines)
- `src/bimkg/validation/validate.py` — pySHACL runner + 구조화 리포트
- 468 violations 의 shape 별 분포 (ERROR 68 + WARNING ~430 + INFO ~1200)

### 왜 채용 시장에서 중요한가

KG 회사 JD 에서 "지식그래프 품질 검증" 은 거의 빠지지 않는 항목입니다.
단순 파싱 에러가 아니라 **의미 수준의 일관성** 을 자동 검증해야 하고, 이건
SHACL 이 표준입니다. 그런데 많은 후보자가 **SHACL 문법만 알고**, "정책 설계
→ 위반 분류 → 자동 리포트 → 상류 피드백" 의 전체 루프를 돌려본 경험이
없습니다.

### 이 프로젝트에서 증명한 것

- 6 shape 각각의 severity (ERROR / WARNING / INFO) 를 **정책적으로** 구분:

| Shape | Severity | 이유 |
|-------|:-------:|------|
| PipingMustHavePipeline | ERROR | pipeline 없는 Piping 은 시공 순서 계산 불가 → 근본 결함 |
| EquipmentMustHaveName | WARNING | 식별만 어려울 뿐 그래프 분석은 가능 |
| PhysicalMustHaveMesh | WARNING | mesh 없으면 시각화만 안 됨 |
| WeightNonNegative | ERROR | 음수 중량은 데이터 오류, 즉시 차단 |
| ObjectMustHaveCoords | ERROR | 좌표 없으면 공간 분석 불가 |
| PipingConfidenceCheck | INFO | 기록 목적 (자동 차단 X) |

- 468 위반의 shape 별 분포를 구조화 리포트로 저장 (반복 검증 가능)
- SHACL 검출 → `docs/findings/` 아카이브 → 상류 PR #3 / Issue #4 로 피드백
  루프 구축 (검증 → 보고 → 수정의 closed loop)

### 면접 언어

> "SHACL 은 만드는 것보다 severity 결정이 어렵습니다. Piping 이 pipeline
> 참조 없이 존재하는 건 시공 순서를 계산할 수 없게 만드는 ERROR 이고,
> mesh 가 없는 건 시각화만 안 되는 WARNING 입니다. 이 구분을 규칙 파일에
> 명시하고 pySHACL 로 자동 검증해서 468 건을 탐지했고, 그중 68 건의 ERROR
> 는 업스트림 DXTnavis PR #3 로 근본 해결했습니다."

---

## 3. 다중 질의 계층의 통합 (GraphRAG)

### 증명 산출물

- `src/bimkg/llm/` — LangGraph ReAct agent + 5 retrieval tools
- `src/bimkg/api/routers/llm.py` — `POST /llm/query` REST endpoint
- 5 tool: SQL Tool (SQLite Gold 218 cols) / FTS5 Tool (전문 검색) / SPARQL
  Tool (rdflib 477K triples) / Cypher Tool (Neo4j 261K edges) / KPI Tool
  (33 사전 계산 지표)

### 왜 채용 시장에서 중요한가

Saltlux TalkEasy, LG CNS Knowlly, Samsung SDS Brity 같은 제품군은 전부
**"사용자 자연어 → 내부 여러 종류의 질의 → 통합 응답"** 구조입니다.
SPARQL 만으로 답할 수 있는 질문은 적고, 보통 그래프 탐색 (Cypher) +
구조화 질의 (SQL) + 전문 검색 (ES/FTS) 를 섞어야 합니다. 이 multi-source
retrieval 패턴이 GraphRAG 의 핵심.

### 이 프로젝트에서 증명한 것

- 자연어 질의를 5 채널로 라우팅하는 ReAct agent 구현 (단순 RAG 가 아님)
  - `"P-10147 파이프라인의 자재 구성?"` → SPARQL Tool (의미 질의)
  - `"Level 7 에서 가장 혼잡한 구역?"` → Cypher Tool (graph path)
  - `"pump"` 검색 → FTS5 Tool (전문 검색)
  - `"Equipment 중 dry_weight > 1000 kg"` → SQL Tool (구조화 필터)
  - `"plant 전체 criticality"` → KPI Tool (사전 계산)
- 5 tool 이 독립된 엔드포인트이지만 LangGraph state 가 단일 agent 에서 조율
- LLM provider abstraction: `claude_client.py`, `gemini_client.py` 둘 다 지원
  (실제 운영은 Gemini 2.5 Flash, 코드 변경 없이 Claude API 로 교체 가능)
- 시스템 프롬프트에 도메인 컨텍스트 + 도구 설명 + few-shot examples 포함

### 면접 언어

> "BIM 질의는 단일 언어로 안 됩니다. '이 파이프라인의 총 중량' 은 SQL 이
> 제일 빠르고, '이 밸브를 잠그면 어떤 객체가 고립되는가' 는 Cypher path
> finding 이 맞고, '유사 설계' 는 SPARQL 의미 질의가 적절합니다. 그래서
> ReAct 에이전트가 질문 유형에 따라 적절한 도구를 선택하게 했고, 각
> 도구는 독립된 엔드포인트로 운영되어 SPARQL 서버만 재기동해도 전체
> 시스템은 돌아갑니다."

---

## 4. Medallion + 온톨로지 결합 아키텍처

### 증명 산출물

- `src/bimkg/ingest/` — Bronze → Silver → Gold (3계층 코드 분리)
- `src/bimkg/ontology/instances.py` — Gold → ABox 변환
- `dags/bim_pipeline_dag.py` — Airflow 3.x DAG (7 tasks × 14 Asset)
- `data/enriched/2026-04-12/bim_objects_enriched.parquet` — Gold 219 cols
- `data/ontology/2026-04-12/owl/bim-objects.ttl` — ABox

### 왜 채용 시장에서 중요한가

KG 회사가 운영하는 실제 지식그래프는 **여러 원천에서 데이터가 오고 시간에
따라 스키마가 변함** 니다. 이때 "원본 → 정제 → 분석용 → RDF" 를 계층화
하지 않으면 스키마 변경 한 번에 전체가 깨집니다. Databricks 가 만든
Medallion 패턴이 표준화된 데이터 레이크 설계로 자리 잡았고, 이걸 KG 와
결합하는 사례가 부족합니다.

### 이 프로젝트에서 증명한 것

- **4계층 분리**:
  - Bronze (raw CSV/XLSX) → 절대 손대지 않음
  - Silver (typed Parquet) → snake_case + SI 단위 + 분류 정규화
  - Gold (enriched Parquet) → 219 컬럼, 6 파생 플래그, 3-단계 신뢰도
  - ABox (RDF triples) → SHACL 통과한 데이터만 흐름
- 각 계층은 **독립 테스트 + 독립 롤백** 가능 (336 tests / 23 files)
- Oracle 12,009 / 12,009 = 100% agreement (상류 C# 분류기와 Python 포팅
  버전이 bit-for-bit 동등)
- Airflow Asset-based DAG 로 lineage 명시 (OpenLineage v2)

### 면접 언어

> "온톨로지를 직접 원본 CSV 위에 얹지 않습니다. 중간에 Gold 테이블 (219
> 컬럼, Parquet) 을 두고 거기서 SHACL 로 검증된 데이터만 ABox 로 흘립니다.
> 이 분리 덕분에 상류 DXTnavis 가 스키마를 변경해도 Silver 계층만 고치면
> 되고, 온톨로지는 그대로 유지됩니다. Oracle 검증으로 12,009 행이 100%
> 일치하는지 매 빌드마다 자동 확인합니다."

---

## 5. 데이터 품질 피드백 루프 — End-to-End Ownership

### 증명 산출물

- `docs/findings/2026-04-12-M1-piping-misclassification/` — audit.py + 5 CSV evidence + 4 PNG figures
- `docs/findings/2026-04-12-M2-adjacency-tiers/` — A/B 검증 결과
- `docs/findings/2026-04-13-M3-parent-box-contamination/` — 6 지표 비교
- DXTnavis 상류 저장소 PR #3 (regex fix) + Issue #4 (parent box flag)

### 왜 채용 시장에서 중요한가

온톨로지/KG 엔지니어가 "기술만 하는 사람" 으로 보이면 senior 포지션에서
거절당합니다. 회사가 찾는 건 **"품질 문제를 발견 → 증거 수집 → 근본 원인
규명 → 해결 + 상류 기여"** 하는 **end-to-end ownership**.

### 이 프로젝트에서 증명한 것

#### M1: Piping 997 건 오분류 (24.8%) 해결

- AABB 기반 분류 정밀도 35.4% 측정 → 증거 수집
- 부분 문자열 매칭 버그 ("Pipe Rack" 안의 "pipe", "steel" 안의 "tee") 식별
- 대안 3가지 평가:
  1. Python 후처리 덮어쓰기 (보수성 ↓, 상류 영원히 안 고쳐짐)
  2. ML 분류기 (레이블링 노력 과다)
  3. **negative lookahead regex** (근본 처방, 커뮤니티 기여 가능) ← 채택
- 동시에 로컬 Python 포팅으로 즉시 적용 + DXTnavis PR #3 로 근본 해결
- classification_confidence 3단계 (HIGH 2,926 / LOW 1,088 / LIKELY_BUG 136)
  로 잔여 uncertainty 정량화

#### M2: AABB 인접성 정밀도 35.4% → 3-tier 분류

- Strong (실제 mesh 겹침 13,422) / Medium (tolerance 내 73,706) / Weak (133,218)
- precedence DAG 의 adjacency_tier 파라미터로 시나리오 선택 가능
- A/B 결과: critical chain 길이가 시나리오별로 88 / 53 / 17 steps
- 효과 크기 측정 후 Strong+Medium 채택 — 의사결정 근거 노트북 재현 가능

#### M3: SP3D Parent Box 271 개가 그래프 66% 오염

- max degree 5,161 → 분포 outlier 탐색으로 발견
- pre-M3 vs post-M3 6 지표 A/B:
  - max degree 5,161 → 388 (92.5% 감소)
  - Louvain zone 29 → 144 (해상도 5배)
  - critical chain 53 → 44 (체인 단축)
- DXTnavis Issue #4 로 업스트림 노출 요청

### 면접 언어

> "AABB 기반 인접성의 정밀도가 35.4% 라는 것은 시공 순서 DAG 의 절반이
> 가짜 의존성이라는 뜻이었습니다. 단순히 필터로 버리지 않고 Strong/Medium/
> Weak 3-tier 로 분류한 뒤, adjacency_tier 파라미터로 분석에서 쓸 수준을
> 선택할 수 있게 만들었습니다. critical chain 길이가 tier 에 따라 88→53→17
> 스텝으로 나왔고, 실무적으로는 Strong+Medium 조합을 채택했습니다. 근거는
> 03_adjacency_tiers.ipynb 의 A/B 차트에 남겼고, 상류 DXTnavis 에는 PR #3
> 으로 정밀도 자체를 개선하는 패치를 보냈습니다."

---

## 6. OWL 추론 + 공유 URI 전략 — 대규모 Triple Store 운영 감각

### 증명 산출물

- `src/bimkg/validation/reasoner.py` — owlrl 적용
- 477,000 RDF triples (3 파일 분할)
  - `bim-objects.ttl` 13 MB (객체 + 데이터 속성)
  - `bim-spatial.ttl` 12 MB (인접 관계만)
  - `bim-shared.ttl` 0.1 MB (공유 개체)
- 505 공유 개체 (Pipeline 147 + PipeRun 334 + Level 10 + Material 4 + Spec 10)

### 왜 채용 시장에서 중요한가

KG 회사 실무에서 RDF 트리플은 수천만 개까지 갑니다. 이때 핵심은:
- **URI 전략** — 같은 개체는 같은 URI 를 쓰게 해야 중복 제거
- **파일 분할** — object/spatial/shared 로 나눠야 diff 와 업데이트가 가능
- **reasoning** — OWL RL 로 symmetric/transitive closure 자동 확장

### 이 프로젝트에서 증명한 것

- Pipeline 147 개를 별도 `bim-shared.ttl` 에 URI 로 한 번만 정의하고,
  PipingComponent 들은 `bim:belongsToPipeline` 을 URI 참조로 가리키게 함
  → 만약 inline string 으로 했다면 ABox 가 3-4 배 커졌을 것
- `adjacentTo` 를 symmetric property 로 선언 → reasoner 가 역방향 트리플
  자동 생성 (220K 원본 → 440K implicit)
- 3 파일 분할로 GitHub diff 추적 가능 (spatial 만 바뀔 때와 object 만
  바뀔 때를 구분 가능, incremental update 의 기반)
- TTL 직렬화 선택 (vs RDF/XML, Turtle, N-Triples) — diff 가독성과 성능의
  균형점

### 면접 언어

> "Pipeline 이라는 개체는 수천 객체가 참조하는데, ABox 를 만들 때마다
> inline string 으로 넣으면 파일 크기가 3-4 배 커집니다. Pipeline 147 개를
> 별도 bim-shared.ttl 에 URI 로 한 번만 정의하고, PipingComponent 들은
> bim:belongsToPipeline 을 URI 참조로 가리키게 해서 전체 ABox 를 25 MB
> 안에서 유지했습니다. 그리고 adjacentTo 를 symmetric 으로 선언해서
> reasoner 가 역방향을 자동 생성하게 만들어 원본 트리플 크기는 절반만
> 저장합니다."

---

## 7. FastAPI + Pydantic 백엔드 — 지식그래프 API 추상화

### 증명 산출물

- `src/bimkg/api/main.py` — FastAPI app entry
- `src/bimkg/api/routers/` — 5 routers × 12 endpoints
- 12 REST endpoints (`/objects/`, `/graph/`, `/ontology/`, `/analytics/`, `/llm/`)
- Pydantic 모델 응답 + Swagger 자동 문서화 (`/docs`)

### 왜 채용 시장에서 중요한가

KG 회사의 backend 엔지니어 업무는 대부분 **"지식그래프/RDF 저장소를 REST
API 로 감싸서 프론트에 제공"** 입니다. SPARQL 을 직접 쓰게 하지 않고
business-level endpoint 로 추상화하는 게 핵심.

### 이 프로젝트에서 증명한 것

| Router | 주요 endpoint | 백엔드 패턴 |
|--------|--------------|-------------|
| `/objects` | `GET /` (필터), `GET /{id}`, `GET /{id}/neighbors` | RESTful resource design |
| `/graph` | `GET /metrics/{id}`, `GET /communities`, `GET /path/{src}/{tgt}` | Graph algorithm 노출 |
| `/ontology` | `GET /classes`, `GET /sparql`, `GET /validate` | KG 직접 노출 + SPARQL passthrough |
| `/analytics` | `GET /summary`, `GET /zones`, `GET /pipelines` | KPI 집계 노출 |
| `/llm` | `POST /query`, `POST /explain/{id}` | LLM agent endpoint |

- Pydantic 으로 RDF 쿼리 결과를 typed response 로 반환 (자동 OpenAPI 스키마)
- Swagger `/docs` 로 자동 문서화 → 프론트 팀과의 contract 명시
- LLM agent 도 REST 로 노출 (`POST /llm/query`) — 외부 시스템 통합 가능

### 면접 언어

> "지식그래프를 외부에 노출할 때 SPARQL endpoint 를 그대로 열어주는 게
> 가장 안 좋은 선택입니다. 내부 ontology 변경이 곧 클라이언트 깨짐으로
> 이어지니까요. 그래서 12 개 REST endpoint 로 business-level 추상화 계층을
> 두고, 내부에서는 SPARQL/Cypher/SQL 을 자유롭게 바꿀 수 있게 만들었습니다.
> Pydantic 모델로 응답 스키마를 고정해서 프론트 팀과의 contract 도 자동
> 문서화 (Swagger /docs) 했습니다."

---

## 8. JD 키워드 대응 표 (채용 공고 매칭)

채용 공고에 자주 등장하는 키워드 vs 이 프로젝트의 증명:

| JD 키워드 | 이 프로젝트의 증명 | 완성도 |
|-----------|--------------------|:-----:|
| RDF / OWL / SPARQL | 477K triples, 28 classes, rdflib SPARQL endpoint | ✅ 완성 |
| Knowledge Graph 구축·운영 | 전체 파이프라인 (Bronze → OWL → Neo4j) | ✅ 완성 |
| Ontology modeling (도메인) | SP3D BIM sibling taxonomy + R4 결정 기록 | ✅ 완성 |
| SHACL validation | 6 shapes, 468 violations 자동 탐지 + severity 정책 | ✅ 완성 |
| OWL Reasoner (Pellet/HermiT/OWL RL) | owlrl 적용, symmetric closure | 🟡 부분 (OWL RL 만, Pellet/HermiT 미사용) |
| Python backend | FastAPI + Pydantic + 336 tests | ✅ 완성 |
| Neo4j / Graph DB | 261K edges, 6 관계 타입, Cypher 쿼리 | ✅ 완성 |
| GraphRAG / LLM + KG | LangGraph 5-tool ReAct agent | ✅ 완성 |
| Natural Language to SPARQL | SPARQL Tool 을 agent 가 라우팅 | 🟡 부분 (auto-generation 이 아닌 tool routing) |
| FTS / ElasticSearch 연계 | SQLite FTS5 (ES 미적용) | 🟡 부분 |
| Java backend (Jena / Fuseki) | Python 만 사용 | ❌ 없음 |
| 대용량 Triple Store (Virtuoso, GraphDB) | rdflib 파일 기반 | ❌ 없음 |
| 다국어 온톨로지 | 한국어/영어 혼합 label | 🟡 부분 (lang tag 없음) |
| 실시간 업데이트 / incremental load | Airflow 배치만 | ❌ 없음 |
| 성능 튜닝 (QPS, latency p95) | 측정 안 됨 | ❌ 없음 |
| Docker / 컨테이너 운영 | Neo4j Docker 만 | 🟡 부분 |
| CI/CD (GitHub Actions) | 미구축 | ❌ 없음 |

**총평**: 12개 핵심 키워드 중 **8개 ✅ + 4개 🟡** (66% full coverage).
핵심 KG 역량은 모두 갖췄고, 부족한 건 **인프라 운영 (Triple Store / 성능
튜닝)** 측면.

---

## 9. 아직 증명하지 않은 것 (다음 프로젝트 후보)

이 프로젝트가 senior level (5+ 년차) 로 가려면 추가해야 할 것들:

### 9.1 Apache Jena Fuseki / Virtuoso / GraphDB 운영

- 현재: rdflib 파일 기반 (SPARQL endpoint 가 메모리 + 파일)
- 목표: Fuseki 를 Docker 로 띄우고 477K 트리플 적재 → SPARQL federated query 시연
- 효과: "수천만 트리플 규모 운영 가능" 이라는 시그널

### 9.2 Natural Language to SPARQL 자동 생성

- 현재: agent 가 "SPARQL Tool 을 선택" 하는 수준 (tool routing)
- 목표: 자연어 → SPARQL 쿼리 문자열 자동 생성 (LangChain SPARQLGenerationChain
  또는 fine-tuned LLM)
- 효과: TalkEasy / Knowlly 같은 제품의 핵심 기능 직접 구현

### 9.3 실시간 업데이트 / Incremental Load

- 현재: 2026-04-12 단일 스냅샷, Airflow 배치만
- 목표: 다음 스냅샷 도착 시 delta detection → ABox 만 부분 갱신하는
  incremental pipeline
- 효과: production-grade KG 운영 패턴

### 9.4 성능 벤치마크 (QPS, p95 latency)

- 현재: 응답 시간 측정 안 됨
- 목표: SPARQL QPS, Cypher latency, agent end-to-end p95 측정 + 최적화
- 효과: "p95 응답이 몇 ms?" 류 질문에 정량 답변 가능

### 9.5 Java/Spring 기반 backend 옵션

- 현재: Python 만 사용
- 목표: Fuseki 위에 Spring Boot 백엔드 (Java) 를 별도로 붙여서 동등한
  REST API 구현 (mirroring)
- 효과: Saltlux/LG CNS 같은 Java 우세 환경에서 차별화

### 9.6 다국어 label + RDF lang tag

- 현재: 한국어/영어 혼합 (lang tag 없음)
- 목표: 모든 label 에 `@ko` / `@en` 명시, SPARQL FILTER lang() 활용
- 효과: 다국어 KG 운영 경험

---

## 10. 솔트룩스/LG CNS/Samsung SDS 지원용 한 줄 요약

> **SP3D BIM 데이터를 OWL 온톨로지(28 classes, 477K triples) 로 모델링하고
> SHACL 6 shape 로 품질 게이트를 구축했으며, Neo4j 지식그래프(261K edges)
> 위에 LangGraph ReAct 에이전트(SPARQL·Cypher·FTS5·SQL·KPI 5 tools)를 얹어
> 자연어 BIM 질의 채널을 완성. 상류 DXTnavis 저장소에 PR #3 과 Issue #4
> 기여로 997 건 오분류와 parent box 오염을 근본 해결.**

이 한 문단이 이력서 필터에서 다음 키워드를 전부 포함:
- **Onto/RDF/SPARQL/SHACL/KG/GraphRAG/Neo4j/LLM agent**
- 동시에 **domain ownership** (DXTnavis 기여) 과 **품질 감각** (SHACL +
  3-단계 confidence) 도 보여줌

---

## 11. 채용 타겟 회사별 강조 포인트

회사 특성에 따라 7 역량 중 강조할 우선순위가 달라집니다:

### Saltlux

- **1순위**: 역량 3 (5-tool ReAct agent — TalkEasy 와 직결)
- **2순위**: 역량 1 (도메인 온톨로지 직접 설계 — 고객사별 onto 구축 업무)
- **3순위**: 역량 5 (피드백 루프 — senior level signal)

### LG CNS Knowlly / Samsung SDS Brity

- **1순위**: 역량 7 (FastAPI 백엔드 — 엔터프라이즈 통합)
- **2순위**: 역량 4 (Medallion 아키텍처 — 대규모 데이터 운영)
- **3순위**: 역량 3 (GraphRAG)

### Stardog / Ontotext / Cambridge Semantics (글로벌)

- **1순위**: 역량 6 (대용량 Triple Store 감각 — Stardog/GraphDB 직접 매핑)
- **2순위**: 역량 1 (온톨로지 모델링 깊이)
- **3순위**: 역량 2 (SHACL — 글로벌 표준 준수도)

### KT / Naver Clova / Kakao i

- **1순위**: 역량 3 (LLM + KG 통합 — 대화형 AI 백본)
- **2순위**: 역량 7 (REST API 백엔드)
- **3순위**: 역량 5 (E2E ownership)

### 대학 연구실 / 정부 출연 연구원 (ETRI 등)

- **1순위**: 역량 1 (온톨로지 설계 + R4 의사결정 기록 = 학술 reproducibility)
- **2순위**: 역량 2 (SHACL + OWL RL 추론)
- **3순위**: 역량 5 (peer-reviewable 한 audit/finding 구조)

---

## 12. 참조

- 코드 저장소: <https://github.com/tygwan/first-ontology-project>
- 단일 포털: [`docs/PROJECT-JOURNAL.md`](../PROJECT-JOURNAL.md)
- 온톨로지 스키마: [`src/bimkg/ontology/schema.py`](../../src/bimkg/ontology/schema.py)
- SHACL shapes: [`src/bimkg/validation/shapes.py`](../../src/bimkg/validation/shapes.py)
- LLM agent: [`src/bimkg/llm/`](../../src/bimkg/llm/)
- Findings: [`docs/findings/`](../findings/)
- DA/DS 심층 분석: [`data-analyst-data-scientist-deep-dive.md`](data-analyst-data-scientist-deep-dive.md)
- R11 portfolio gap: [`r11-portfolio-gap-analysis.md`](r11-portfolio-gap-analysis.md)
- Notion portfolio (외부): <https://www.notion.so/Refinery-Facility-Ontology-Analytics-3405a4e1f87881d08fd4f9ed41234793>

---

*Last updated: 2026-04-14*
