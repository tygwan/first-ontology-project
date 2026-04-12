# Portfolio PAAR Analysis — Knowledge Graph / AI Service 역량 점검

> 이 문서는 프로젝트 경험을 PAAR 구조 (Problem → Analyze → Action → Result) 로 정리하여
> 역량을 논리적으로 어필할 수 있도록 준비하는 참조 문서입니다.
>
> 각 항목의 강/약/보강 방법을 솔직하게 기록합니다.

---

## 1. 도메인 분석 기반 데이터 모델링 및 온톨로지 설계

### PAAR

**Problem**: SP3D 플랜트 BIM 모델 12,009 객체에 136개 속성이 있지만, 클래스 계층이 없고 6개 분류 라벨만 존재. 객체 간 의미 관계가 CSV 에 평면적으로 저장되어 있어 질의·검증·추론이 불가능한 상태.

**Analyze**: OWL 온톨로지의 top-level 구조를 3가지 옵션으로 검토.
- Option A: BIMObject ‖ AnalysisArtifact (sibling) → SHACL positive rule 가능
- Option B: 단일 트리 → negative rule 필요, 복잡
- Option C: 평탄 → 중간 추상화 상실

Equipment 서브클래스도 3가지: 평탄(A) vs Eqp Type 0 강제(B) vs Unclassified bucket 포함(C).

**Action**: D10 sibling 구조 채택 (Option A). Equipment 는 Q2-C (7 서브클래스 + UnclassifiedEquipment). 8개 구조적 질문 (Q1~Q8) 에 대해 각각 옵션 비교 + 추천 → 사용자 승인 후 구현.

**Result**: 28 OWL classes, 8 object properties, 32 data properties. 12,009 개체 100% 타이핑 (물리 7,840 + 계층 3,624 + 분석 145 + 기타 400). SPARQL cross-validation 12개 쿼리 통과.

### 어필 포인트
- **의사결정 과정이 문서화됨**: `methodology-data-logic.md` §7, §11, PROJECT-JOURNAL D10/D11
- **숫자**: 28 classes, 477K triples, 12 SPARQL 검증

### 부족한 것
- 상위 온톨로지 (BFO, DOLCE) 와의 정렬 미검토 — 학술적 깊이 부족
- 다른 도메인 (건축, 조선 등) 온톨로지와의 비교 미수행

### 보강 방법
- ifcOWL (IFC 표준 온톨로지) 와의 매핑 관계를 1페이지로 정리하면 "표준 인지" 증명
- BFO 의 Continuant/Occurrent 구분을 BIMEntity 에 매핑하면 "상위 온톨로지 이해" 증명

---

## 2. RDF/OWL 기반 Knowledge Graph 구축

### PAAR

**Problem**: 12,009 객체 × 218 컬럼의 Gold 테이블을 RDF 그래프로 변환해야 하는데, (1) 직렬화 포맷 선택, (2) 파일 분할 전략, (3) 공유 개체 (Pipeline, Material 등) URI 관리가 필요.

**Analyze**: 포맷 A(Turtle) vs B(N-Triples) vs C(OWL/XML). 분할 A(단일) vs B(클래스별) vs C(관심사별). Pipeline 표현 A(문자열) vs B(Named Individual) vs C(Blank Node). 각각 SPARQL 편의성, 파일 크기, 재생성 독립성으로 비교.

**Action**: Turtle (가독성) + 관심사별 3파일 (objects/spatial/shared) + Named Individual (URI deduplication). 총 5개 의사결정을 Q4~Q8 로 기록.

**Result**: bim-objects.ttl 13MB + bim-spatial.ttl 12MB + bim-shared.ttl 0.1MB = 477K triples. 505 공유 개체 (Pipeline 147, PipeRun 334, Level 10, Material 4, Spec 10). 생성 시간 35초.

### 어필 포인트
- **trade-off 명시적**: Q4~Q8 각각 3 옵션 + 근거 → `methodology-data-logic.md` §7
- **재현 가능**: `generate_tbox()` + `generate_abox()` 함수 호출로 전체 재생성

### 부족한 것
- OWL reasoning (subclass inference, symmetric closure) 미구현
- SPARQL endpoint 없음 (rdflib in-memory 만)
- 대용량 성능 테스트 미수행 (477K 는 소규모)

### 보강 방법
- owlrl 로 추론 + 추론 트리플 수 보고 (예: "symmetric closure 로 adjacentTo 110K → 220K") → 5줄 코드
- Apache Jena Fuseki Docker → SPARQL endpoint → "triplestore 운영 경험" 추가 (30분)
- 477K → 4.7M (10x synthetic) 로 로드 시간/쿼리 시간 벤치마크 → "스케일 인지" 증명

---

## 3. Python 기반 백엔드 서비스 개발

### PAAR

**Problem**: C# 백엔드가 생성한 BIM 데이터를 Python 단일 저장소에서 전체 처리해야 함. 데이터 정제 → 온톨로지 → 검증 → 분석 → 내보내기까지 재현 가능한 파이프라인 필요.

**Analyze**: 스크립트 모음 vs 모노리포 패키지 vs 마이크로서비스. 12K 규모에서 마이크로서비스는 과도. 모노리포 패키지로 `bimkg` namespace 아래에 모듈별 분리.

**Action**: `src/bimkg/` 아래 4개 서브패키지 (ingest, ontology, validation, analytics). pytest 305 테스트. uv + ruff 도구 체인. config.py 단일 경로 관리.

**Result**: 15 Python 모듈, 305 tests, 100% 테스트 통과. 전체 파이프라인 재실행 67초.

### 어필 포인트
- **테스트 커버리지**: 305 tests, oracle 100% agreement, pinned count 검증
- **아키텍처**: Medallion 4계층, config 중앙화, dev-standards 규칙 적용
- **코드 품질**: ruff lint/format, type hints

### 부족한 것
- ❌ Java 경험 없음 (JD 요구)
- ❌ REST API 없음 (Phase 6 미구현)
- async/await, 동시성, 캐싱 등 백엔드 서비스 패턴 미적용

### 보강 방법
- **Phase 6 FastAPI**: `/objects`, `/graph`, `/ontology`, `/llm` 엔드포인트 → "REST API 서비스 개발" 직접 증명
- Java: 이 프로젝트에서 보강 불가. 별도 학습 필요. 다만 "Python 능숙 + Java 학습 의지" 로 어필
- FastAPI 에 Redis 캐싱 + background tasks 추가하면 "백엔드 패턴 이해" 증명

---

## 4. LLM 기반 AI 서비스 (RAG, AI Agent) 연계 개발

### PAAR

**Problem**: 아직 미구현 (Phase 5).

**Analyze**: retrieval 기반은 준비됨:
- 구조화 데이터: Gold parquet 218 cols, SQLite FTS5
- 시맨틱 검색: OWL/SPARQL 477K triples
- 그래프 탐색: Neo4j 261K edges + Cypher
- 분석 결과: 33 KPIs, 144 zones, precedence DAG

**Action**: 미착수. Phase 5 계획: multi-source retriever (SQL + SPARQL + Cypher) → Claude API → 자연어 BIM 질의.

**Result**: 없음.

### 어필 포인트 (현재)
- retrieval 기반 인프라가 4종 준비됨 — "RAG 할 줄 아는 사람이 아니라 RAG 에 필요한 것을 아는 사람"

### 부족한 것
- ❌ 실제 RAG 구현 없음
- ❌ LangChain / LlamaIndex 사용 경험 없음
- ❌ prompt engineering, tool use, agent 패턴 미경험 (코드 레벨)

### 보강 방법 (가장 시급)
- **Phase 5 를 LangChain 으로 구현**: SQLite + SPARQL + Neo4j 를 tool 로 등록 → multi-tool RAG agent
- "P-10147 파이프라인에 뭐가 있어?" → LangChain agent 가 SPARQL 생성 → 결과 요약
- 구현하면: "LLM 프레임워크 경험" + "RAG 개발" + "AI Agent" 3개를 동시에 획득
- 예상 소요: 2~3일

---

## 5. 데이터 통합 및 메타데이터 관리

### PAAR

**Problem**: DXTnavis 의 11개 파일 (CSV, XLSX, JSON, TTL) 이 서로 다른 스키마, 인코딩, 명명 규칙을 가짐. 원본 136개 컬럼에서 의미 있는 218개 컬럼의 Gold 테이블로 통합해야 함.

**Analyze**: 컬럼 명명 전략 (snake_case + prefix), 타입 변환 규칙 (SP3D 문자열 → SI float), lineage 보존 전략 (원본값 유지 vs 변환값 병기). XLSX 의 한국어 컬럼명 처리 (항목→nav_item, 재질→nav_material 등).

**Action**: `xlsx_loader.py` 에 `normalize_column_name()` 구현 (prefix 분류 + snake_case + 충돌 검출). `unit_parser.py` 에 임페리얼→SI 변환. `clean.py` 에 5개 플래그 파생 + confidence layer. lineage 4 컬럼 추가. 전체 논리를 `methodology-data-logic.md` 12 섹션으로 문서화.

**Result**: 218 컬럼 Gold (94 sp3d + 37 nav + 87 파생). lineage 100% 추적 가능. 한국어 컬럼 0개 (전체 영문 변환). 44 단위 파서 테스트.

### 어필 포인트
- **데이터 계보 (lineage)**: 원본→변환 과정이 12 섹션 문서 + 코드 + 테스트로 삼중 검증
- **naming convention**: 한국어 → 영문 접두사 체계적 변환 (20개 카테고리 매핑)
- **dev-standards R9 provenance**: SNAPSHOT 상수 고정, ingested_at 타임스탬프

### 부족한 것
- 메타데이터 카탈로그 도구 (Apache Atlas, DataHub) 경험 없음
- 데이터 거버넌스 프레임워크 (정책, 소유권, 접근 제어) 미적용
- CDC (Change Data Capture) 나 실시간 통합 경험 없음

### 보강 방법
- `methodology-data-logic.md` 자체가 수동 메타데이터 카탈로그 역할 → "메타데이터 설계 경험" 으로 어필 가능
- 컬럼별 메타데이터 (dtype, source, transform_rule, fill_rate) 를 JSON schema 로 내보내면 "데이터 카탈로그 자동화" 사례가 됨

---

## 6. 지식그래프 기반 데이터 품질 관리

### PAAR

**Problem**: XLSX 분류기의 오류 (M1: 997건), adjacency 의 AABB 오염 (M2: 3-tier), parent box 오염 (M3: 66%) 을 체계적으로 탐지하고 수정해야 함. 수동 검토는 12K 객체에서 불가능.

**Analyze**: SHACL (선언적 규칙) vs Python 코드 (절차적 검증) vs SPARQL constraint (ad-hoc). SHACL 은 OWL 위에서 작동하므로 온톨로지가 있으면 선언적 규칙이 가장 유지보수 용이.

**Action**: 6 SHACL shapes 작성 (PipingMustHavePipeline ERROR, PhysicalMustHaveMesh WARNING, WeightNonNegative ERROR 등). pySHACL runner 로 자동 실행. Finding 프로세스 (R3 규칙): 발견 → 아카이브 → 분석 → 수정 → 검증 → DXTnavis 이슈 제출.

**Result**: 468 violations 탐지 (mesh 400 + pipeline 68). M1/M2/M3 3건 finding, 각각 5-section README + audit script + 시각화 + DXTnavis Issue (#2, #4). 3건 모두 Resolved.

### 어필 포인트
- **프로세스가 체계적**: 발견 → 아카이브 (6-step) → 수정 → 테스트 재기준선 → 원천 이슈 제출
- **선언적 검증 + 절차적 보완**: SHACL shapes + Python confidence layer
- **외부 이슈 관리**: DXTnavis Issue #2, #4 — 원천 데이터 품질까지 소통

### 부족한 것
- SHACL 규칙이 6개로 적음 — 산업 현장에서는 수십~수백 개
- SHACL-SPARQL (커스텀 제약) 미사용 — 기본 property shape 만
- 품질 대시보드 (violation trend, resolution rate) 없음

### 보강 방법
- SHACL-SPARQL 규칙 2~3개 추가 (예: "파이프라인 멤버 간 centroid 거리가 100m 초과하면 경고")
- violation 결과를 CSV 로 내보내서 시계열 추적 가능하게 하면 "품질 모니터링" 사례

---

## 7. Neo4j / Graph Database

### PAAR

**Problem**: 12,009 BIM 객체와 220K 공간 관계를 그래프로 표현하여, 시공 순서 경로 탐색, 파이프라인 시각화, 존 간 의존성 분석을 Neo4j Cypher 로 수행해야 함.

**Analyze**: Neo4j (property graph) vs RDF triplestore (SPARQL) vs NetworkX (in-memory). 탐색형 질의는 Neo4j 가 강점 (Cypher 패턴 매칭). 분석은 NetworkX (centrality, community). 선언적 검증은 SPARQL/SHACL. → 세 가지 병행.

**Action**: Neo4j 5 Docker 운영. 6종 관계 모델링 (ADJACENT_TO, MUST_PRECEDE, HAS_PARENT, BELONGS_TO_PIPELINE, IN_ZONE, ZONE_PRECEDES). 각 관계에 속성 (relationType, edgeType, onCriticalPath 등). `scripts/neo4j_import.sh` 로 재현 가능. 공정계획 Cypher 질의 6종 작성.

**Result**: 12,185 nodes + 261K edges. 시공 순서 시각화, 파이프라인 격리 분석, 존 간 의존성 질의를 Neo4j Browser 에서 실행.

### 어필 포인트
- **관계 모델 설계**: 6종 관계의 의미와 속성을 도메인에서 도출 → `methodology-data-logic.md` §10
- **Cypher 질의**: 공정계획, 파이프라인 탐색, 존 경계 분석 등 실무형 질의
- **운영**: Docker 기반 재현 가능 스크립트

### 부족한 것
- 12K nodes 는 소규모 — 수백만 노드 경험 없음
- Cypher 쿼리 최적화 (EXPLAIN/PROFILE) 미수행
- Neo4j clustering, backup, monitoring 미경험
- APOC 프로시저, GDS 라이브러리 미사용

### 보강 방법
- GDS (Graph Data Science) 라이브러리로 Louvain/PageRank 를 Neo4j 안에서 실행 → "NetworkX→GDS 마이그레이션" 사례
- EXPLAIN/PROFILE 로 Cypher 쿼리 3개의 실행 계획 분석 → "쿼리 최적화 인지"

---

## 8. 데이터 표준 및 메타데이터 설계

### PAAR

**Problem**: SP3D 원본 데이터는 한국어/영문 혼합 컬럼명, 단위 불일치 (imperial/metric), 플랫폼 의존적 인코딩. 이를 일관된 표준으로 정규화해야 다운스트림 (OWL, Neo4j, PowerBI) 에서 사용 가능.

**Analyze**: 명명 규칙: camelCase vs snake_case vs 원본 유지. 단위: 원본 보존 vs SI 변환 vs 양쪽 병기. 컬럼 접두사: 카테고리별 prefix (sp3d_, nav_, si_) vs 평탄.

**Action**: snake_case + prefix 체계 (sp3d_ 94개, nav_ 37개, 파생 87개). SI 변환 컬럼과 원본 문자열 병기. `EXPLICIT_RENAMES` 딕셔너리로 특수 매핑. 충돌 검출 로직 (`normalize_columns` 에서 중복 시 ValueError). dev-standards R9 provenance (SNAPSHOT 고정, ingested_at).

**Result**: 218 컬럼 Gold, 한국어 0개, 컬럼 충돌 0건. 30개 unit test 로 변환 정확도 검증.

### 어필 포인트
- 명명 체계가 **코드로 강제됨** (테스트에서 한국어/파이프 문자 검출)
- lineage 가 컬럼 레벨까지 추적 가능

### 부족한 것
- ISO 15926 (플랜트 데이터 표준) 미참조
- 데이터 사전 (data dictionary) 별도 미생성
- 메타데이터 도구 (DataHub, Apache Atlas) 미사용

### 보강 방법
- 218 컬럼의 data dictionary 를 JSON/YAML 로 자동 생성 → "메타데이터 자동화"
- ISO 15926 의 주요 클래스와 우리 OWL 클래스의 매핑 표 1페이지 → "표준 인지"

---

## 9. A/B 테스트 기반 의사결정 (프로젝트 고유 역량)

### PAAR

**Problem**: 온톨로지 설계, 시공 존 정의, adjacency 필터링 등 주요 결정에서 "이게 더 나을 것 같다" 는 추론만으로는 최적 선택을 보장할 수 없음.

**Analyze**: 웹 A/B 테스트와 달리 엔지니어링 결정은 한 번 내리면 되돌리기 어려움. 측정 가능한 결정에 대해 최소 2개 대안을 실제로 구현하고 지표로 비교하는 패턴 필요.

**Action**: 3회 A/B 테스트 실행:
1. Grid 15m vs Louvain → 4개 CM 지표 비교 → Louvain 채택
2. All vs Strong vs Strong+Medium adjacency → critical chain 비교 → S+M 채택
3. pre-M3 vs post-M3 → 6개 지표 비교 → clean graph 채택

**Result**: 각 결정이 정량적 근거를 가짐. 노트북에 시각화 + 해석 포함. dev-standards R10 으로 일반화 예정.

### 어필 포인트
- **"의견이 아니라 데이터로 결정한다"** — 면접에서 가장 설득력 있는 자세
- 각 A/B 의 지표, 승자, 이유가 명확히 기록됨

---

## 우선순위 보강 로드맵

| 순위 | 항목 | 소요 | 효과 (JD 매핑) |
|:----:|------|:----:|---------------|
| **1** | Phase 5: LangChain RAG | 2~3일 | LLM + RAG + AI Agent + 프레임워크 — **4개 동시** |
| **2** | Phase 6: FastAPI | 1~2일 | REST API + 백엔드 서비스 — **2개 동시** |
| **3** | Fuseki triplestore | 30분 | 온톨로지 저장소 경험 + SPARQL endpoint |
| **4** | OWL reasoning (owlrl) | 2시간 | 추론 경험 + inferred triples 수치 |
| **5** | Neo4j GDS | 2시간 | GDS 라이브러리 + 쿼리 최적화 |
| **6** | Data dictionary JSON | 1시간 | 메타데이터 자동화 |
| **7** | ISO 15926 매핑 표 | 2시간 | 산업 표준 인지 |

> 1+2 를 완성하면 JD 의 "자격요건" 전항목 커버. 3~7 은 "우대사항" 강화.

---

*Last updated: 2026-04-13*
*Review status: 작성 완료, 사용자 리뷰 대기*
