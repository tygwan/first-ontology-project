# 직무 역량 포트폴리오 — Refinery Facility Ontology Analytics

> 이 문서는 BIM Knowledge Graph Pipeline (사내명: **Refinery Facility
> Ontology Analytics**) 프로젝트의 산출물을 **ML/AI·데이터·백엔드 직군**
> 채용·면접 관점에서 **직무 역량별로 재정렬** 한 자료입니다.
>
> 특정 회사·직무에 특화하지 않고 **프로젝트의 모든 디테일을 보존** 합니다.
> 지원 시점에 이 문서에서 JD 에 해당하는 역량만 선택적으로 추출하는
> 방식입니다 — source of truth 는 완전·중립, 특화는 지원 시점에.
>
> 각 역량 축마다 ① 증명 산출물 ② 왜 채용 시장에서 중요한가 ③ 면접 언어 를
> 명시합니다.
>
> 작성 기준 스냅샷: `2026-04-12`
> 작성 일자: `2026-04-14`
> 코드 경로는 모두 `/home/taegwan-dev/dev/first-ontology-project` 기준
>
> 본 문서는 dev-standards [R11 v0.2.0](https://github.com/tygwan/dev-standards)
> 의 single-source marker 규약을 따릅니다 — 섹션 헤더의
> `# 문제해결` / `# 구현` / `# 크로스역량` 마커가 이력서 view / portfolio view
> 자동 렌더링 키입니다.

---

## 0. 한눈에 보기

### # 크로스역량 — 한 줄 결론

> **정유시설 SP3D 도면 12,009 객체를 OWL 온톨로지(28 classes, 477K triples)
> · Neo4j 그래프(261K edges) 로 모델링하고, FastAPI 12 endpoints +
> LangGraph ReAct 에이전트(5-tool RAG, LLM-agnostic) + Medallion 4계층
> 거버넌스 스택까지 단독 구현한 end-to-end 데이터·AI 프로젝트.**

### 5개 핵심 역량 축

| # | 역량 축 | 핵심 증명 | 해당 직군 JD 키워드 |
|:-:|---------|-----------|---------------------|
| 1 | **데이터 파이프라인 구축·최적화** | Medallion 4계층 + Airflow 3.x DAG (7 tasks · 14 Assets) + OpenLineage v2 ColumnLineage | Data Engineer / MLOps / ML Engineer |
| 2 | **실험 설계 & A/B 테스트** | dev-standards R10 (Decision Validation) 자체 정립 + 3건 적용 | Data Scientist / ML Engineer / Product Analyst |
| 3 | **AI 모델 ↔ API 백엔드 연동** | FastAPI 12 endpoints + LangGraph ReAct 5-tool agent (LLM-agnostic) | ML Engineer / AI Engineer / Backend |
| 4 | **데이터 분석 & 피처 엔지니어링** | Gold 219 cols + 파생 피처 6종 + 5 notebooks + 25 PNGs | Data Analyst / Data Scientist |
| 5 | **문제 정의 → 데이터 기반 해결** | M1/M2/M3 finding 5단계 archive + DXTnavis PR #3 + Issues #2/#4 | 전 직군 공통 (문제 해결 역량) |

**보완 역량 축** (위 5개의 상위 카테고리로 분화되는 추가 증명):

| # | 역량 축 | 상세 참조 |
|:-:|---------|-----------|
| 6 | 온톨로지·지식그래프 설계 | [`ontology-kg-engineer-perspective.md`](ontology-kg-engineer-perspective.md) 7가지 역량 |
| 7 | 데이터 분석·통계 방법론 | [`data-analyst-data-scientist-deep-dive.md`](data-analyst-data-scientist-deep-dive.md) 11 섹션 |

**한 줄 결론**: ML/AI 직군·데이터 직군·백엔드 직군 모두에 **방어 가능한 mid-junior
수준** 실증 자료. senior 수준은 §8 의 honest gap (TF/PyTorch, 직접 DL 학습)
을 보완하면 도달.

---

## 1. 프로젝트의 3가지 핵심 차별점

### # 크로스역량 — 1.1 도메인 모델링 경험 (Plant BIM)

대부분의 포트폴리오는 **public dataset (MNIST · Titanic · NYC Taxi)** 기반
입니다. 이 프로젝트는 **실제 산업 도메인 데이터** 로 12K 객체 × 110K 공간
관계 스케일을 다뤘습니다.

**스케일 증명**:
- **12,009 BIM 객체** (Equipment 851 + Piping 3,062 + Structure 4,840 + Other 3,256)
- **110,173 공간 인접 관계** (AABB intersection 기반)
- **477K OWL triples** (28 classes · 8 object properties · 32 data properties)
- **261K Neo4j edges** (6 관계 타입)

**도메인 transfer 가능성**:

| 산업 카테고리 | 매칭 경로 |
|--------------|-----------|
| Plant / 제조 (정유·화학·배터리·반도체) | BIM 객체 온톨로지 → 공정 설비 디지털 트윈 직접 인접 |
| B2C 소비재 / 유통 | SKU·성분·카테고리 지식그래프 구조 동일 (28 classes 패턴) |
| 금융·보험 | 상품·계약·리스크 관계 그래프 (Neo4j 261K edges 경험 transfer) |
| 의료 / 바이오 | 질병·약물·유전자 지식그래프 (SNOMED·MeSH 계열 ontology 유사 구조) |
| 통신 / 모빌리티 | 네트워크 · 경로 그래프 (인접 관계 패턴 동일) |

이 프로젝트의 가치는 **"특정 도메인 한정" 이 아니라 "복잡한 도메인 엔터티를
온톨로지 + 그래프 + LLM 으로 통합하는 아키텍처 패턴"** 이 모든 산업에
transfer 가능하다는 점입니다.

### # 크로스역량 — 1.2 LLM-Agnostic Architecture

현재 구현은 **Google Gemini 2.5 Flash** 를 사용하지만, LangGraph 의 모델
어댑터 추상화로 **모델 교체가 1줄 변경** 입니다.

```python
# src/bimkg/llm/agent.py — 현재
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", ...)

# OpenAI GPT-4o
llm = ChatOpenAI(model="gpt-4o", ...)

# Anthropic Claude
llm = ChatAnthropic(model="claude-opus-4-5", ...)

# LG AI Research EXAONE (OpenAI-compatible endpoint)
llm = ChatOpenAI(base_url="https://exaone-api.../v1", model="exaone-3.5", ...)

# Self-hosted (Ollama / vLLM)
llm = ChatOllama(model="llama3.1:70b", ...)
```

**5개 retrieval tool (SQL · FTS5 · SPARQL · Cypher · KPI) + ReAct 프롬프트
+ few-shot examples** 는 모델과 무관하게 재사용 가능합니다. 이는 **모델
선택권이 제약된 엔터프라이즈 환경 (자체 LLM · 온프레미스 · 정책상 외부 API
금지 등)** 에 즉시 transfer 가능한 자산임을 의미합니다.

### # 크로스역량 — 1.3 엔터프라이즈 거버넌스

대기업·공공·금융·규제 산업이 가장 중시하는 것은 "혼자서 빠르게" 가 아니라
**"여러 명이 재현·검증·감사할 수 있는가"** 입니다. 이 프로젝트는 처음부터
그 관점으로 설계됨:

| 거버넌스 축 | 증명 |
|------------|------|
| **재현성** | `SNAPSHOT="2026-04-12"` 단일 변수 pin · 336 tests · `scripts/verify_phase1.py` 1회 출력 검증 |
| **데이터 lineage** | OpenLineage v2 (14 events · ColumnLineage facets) + lineage impact 분석 24 datasets |
| **품질 게이트** | SHACL 6 shapes / 468 violations 자동 탐지 + severity 정책 (CRITICAL/MAJOR/MINOR) |
| **변경 추적** | 4-column lineage scheme (source / source_id / extracted_at / classifier_version) |
| **표준 정립** | dev-standards R1~R11 자체 작성 (다른 프로젝트에 재사용 가능한 작업 표준) |

처음부터 "혼자 쓰는 스크립트" 가 아니라 **"팀이 승계 가능한 자산"** 으로
설계한 reflex 가 핵심입니다. R4 결정 기록 D1~D14 가 그 증거.

---

## 2. 역량 #1 — 데이터 파이프라인 구축·최적화

### # 구현 — 증명 산출물

- `src/bimkg/ingest/` — **Medallion 4계층** (Bronze → Silver → Gold → Ontology)
- `src/bimkg/ingest/sqlite_writer.py::run_phase_1a()` — 단일 진입점 파이프라인
- **Airflow 3.x DAG** (`dags/bim_pipeline_dag.py`) — 7 tasks, 14 Assets, dataset-aware scheduling
- **OpenLineage v2** events 14건 (`src/bimkg/lineage/openlineage_emitter.py`) — Schema·ColumnLineage facets, 295 KB JSONL
- **ydata-profiling** Gold 219 cols (`docs/reference/profiling/2026-04-12/`) — 270 quality alerts
- **Warehouse 카탈로그** (`docs/reference/warehouse-catalog/2026-04-12/`) — SQLite 7 tables · 62.9 MB · catalog.md + catalog.json
- **Lineage impact 분석** (`docs/reference/lineage/2026-04-12/`) — 24 datasets · downstream/upstream maps · lineage-graph.png 822 KB
- 데이터 물리 위치:
  - Bronze: `data/raw/dxtnavis/2026-04-12/` (CSV/XLSX/JSON, 읽기 전용)
  - Silver: `data/clean/2026-04-12/` (Parquet)
  - Gold: `data/enriched/2026-04-12/` (Parquet + SQLite)
  - PowerBI: `data/powerbi/2026-04-12/` (10 CSV star schema)
  - Ontology: `data/ontology/2026-04-12/{object_types,link_types,owl}/`

### # 크로스역량 — 왜 채용 시장에서 중요한가

"데이터 파이프라인 구축" 은 Data Engineer · ML Engineer · MLOps · AI Engineer
공고에 빠지지 않는 항목입니다. 하지만 공고가 요구하는 것은 단순 ETL 스크립트가
아니라 **"다중 소스 데이터의 노이즈를 제거하면서 lineage 와 재현성을 유지하는"
거버넌스 능력** 입니다. Medallion + OpenLineage 조합은 이 두 요구를 모두
충족하는 **현재 업계 표준 패턴** 입니다.

특히 **컬럼 단위 lineage (ColumnLineage facet)** 적용 경험은 흔치 않으며,
다중 시스템 환경 (MES · ERP · CRM · POS · CAD 등) 에서 변경 영향 추적이
필수인 엔터프라이즈 환경에 직접 transfer 됩니다.

### 면접 언어

> "BIM 데이터를 처리할 때 단순히 CSV 를 읽고 변환하는 게 아니라 Bronze/
> Silver/Gold/Ontology 4계층 Medallion 으로 분리했습니다. Bronze 는 절대
> 수정하지 않고 스냅샷 날짜로 pin 하고, Silver 에서 단위 정규화, Gold 에서
> 파생 피처 (classification confidence, AABB tier, parent_box flag) 를 추가하는
> 식입니다. Airflow 3.x 의 dataset-aware scheduling 과 OpenLineage v2
> ColumnLineage facet 으로 컬럼 단위 변경 추적까지 적용해서, 한 컬럼이
> 바뀌면 영향 받는 24개 downstream dataset 을 즉시 식별할 수 있습니다.
> 이 구조는 다중 시스템 통합 환경 (MES · ERP · CRM 등) 에 그대로 transfer
> 가능합니다."

---

## 3. 역량 #2 — 실험 설계 & A/B 테스트 (R10 Decision Validation)

### # 구현 — 증명 산출물

- **dev-standards R10** = Decision Validation / A/B Testing 룰 자체 정립
- 3건의 A/B 비교 문서화:

| # | 실험 | A안 | B안 | 채택 근거 |
|:-:|------|-----|-----|-----------|
| 1 | **시공 존 분할** | 균등 Grid (X×Y 격자) | **Louvain 커뮤니티 ✅** | Modularity 0.42 vs Grid 0.18, 도메인 의미 보존 |
| 2 | **Adjacency 품질** | AABB 단일 거리 | **3-tier 분류 (HIGH/MED/LOW) ✅** | 정밀도 35.4% → tier 분리로 HIGH 의 정밀도 ~80% |
| 3 | **Parent Box 처리** | 그대로 유지 | **`is_parent_box` flag + 인접 제외 ✅** | 448개 객체가 인접 66% 오염 → 제거 후 통계 안정화 |

- 결정 기록: `docs/PROJECT-JOURNAL.md §4` D1~D14
- 상세 공식: `docs/analysis/data-analyst-data-scientist-deep-dive.md §4`

### # 크로스역량 — 왜 채용 시장에서 중요한가

"실험 설계 및 결과 분석 (A/B 테스트 포함)" 은 Data Scientist · Product
Analyst · ML Engineer 공고의 필수 항목입니다. 채점자는 **"감" 으로
의사결정하지 않고 수치 근거로 채택/기각 trace 를 남길 수 있는지** 를 봅니다.

A/B 가 단순히 "두 안을 만들어 보여주는 것" 이 아니라:
1. **공정한 비교 metric 정의** (Modularity, Precision, 분포 안정성)
2. **두 안의 산출물을 동일 입력으로 측정**
3. **결정과 근거를 후속 합류자가 1년 후에도 추적 가능** 하도록 R4 결정 기록에 남김

이 3단계가 모두 갖춰진 portfolio 는 후보자 풀에서 흔치 않습니다. 특히
**dev-standards R10 을 자체 룰로 문서화·정립** 한 것은 개인 역량을 넘어
**팀 작업 표준을 제안·정립할 수 있다** 는 리더십 시그널입니다.

### 면접 언어

> "공정 데이터를 시공 존으로 나눠야 했는데, 처음에는 단순히 X-Y 격자로
> 균등 분할했습니다. 하지만 modularity 를 측정해보니 0.18 로 도메인 구조를
> 전혀 보존하지 못했습니다. 그래서 Louvain 커뮤니티 검출로 A/B 비교했고
> modularity 0.42 + 의미 단위 보존이 확인돼 채택했습니다. 이 결정 trace 를
> dev-standards R10 (Decision Validation) 룰로 정립해서, 모든 구조적 결정에
> 두 안 이상의 비교와 metric 측정을 강제하는 작업 표준으로 삼았습니다.
> 같은 패턴을 제품 실험·마케팅 A/B·모델 후보 선정 등에 그대로 적용 가능합니다."

---

## 4. 역량 #3 — AI 모델 ↔ API 백엔드 연동 (LLM-Agnostic)

### # 구현 — 증명 산출물

- **FastAPI** `src/bimkg/api/main.py` — **12 REST endpoints**, Pydantic 검증,
  Swagger 자동 문서, 실행: `uvicorn bimkg.api.main:app`
- **LangGraph ReAct agent** `src/bimkg/llm/agent.py` — 현재 Gemini 2.5 Flash,
  **LLM 어댑터 1줄 교체** (Claude · GPT · EXAONE · Llama 등 모두 swap 가능)
- **5개 retrieval tool** `src/bimkg/llm/tools.py`:

  | Tool | 용도 | 백엔드 |
  |------|------|--------|
  | `sql_tool` | 정량 집계 (count, group-by) | SQLite (Gold warehouse) |
  | `fts_tool` | 자연어 검색 (객체명, 설명) | SQLite FTS5 |
  | `sparql_tool` | 클래스 계층, 속성 기반 질의 | rdflib (OWL graph) |
  | `cypher_tool` | 인접·경로 (몇 hop) 질의 | Neo4j (261K edges) |
  | `kpi_tool` | 도메인 KPI 33종 (Criticality · Accessibility · Corrosion · Isolation) | precomputed JSON |

- **System prompt 3-part 구조** `src/bimkg/llm/prompts.py` — 도메인 + 도구 가이드 + few-shot examples
- **테스트** 17 LLM tests + 14 API tests + 2 E2E (LLM API 키 있을 때만)

### # 크로스역량 — 왜 채용 시장에서 중요한가

"API 및 백엔드 + AI 모델 연동" 은 **ML Engineer · AI Engineer · Backend
Engineer 공고의 핵심 항목** 이며, 최근에는 "**GraphRAG / RAG / tool-calling
agent 경험**" 으로 세분화되는 추세입니다.

**5-tool retrieval 아키텍처의 차별점**:
- 단순 vector search 기반 RAG 를 넘어 **정량(SQL) + 검색(FTS) + 구조(SPARQL·
  Cypher) + 도메인(KPI)** 4축 통합
- agent 가 질의 유형에 따라 **자동 라우팅**, 복합 질의 시 **다중 tool 조합**
- **LLM-agnostic** 설계로 엔터프라이즈 LLM 제약 환경 대응 가능

**실제 agent 응답 패턴**:
- "냉각수 펌프 근처에 있는 모든 배관 설비를 찾아줘" → `cypher_tool` 라우팅
  → 3-hop 인접 + Equipment 필터 → 자연어 응답
- "Equipment Criticality 가 가장 높은 10개와 그 이유는?" → `kpi_tool` +
  `sql_tool` 조합 → 정량 + 도메인 설명

### 면접 언어

> "지식그래프를 단순히 데이터베이스로 두지 않고, LangGraph 의 ReAct agent 로
> 자연어 질의 채널을 만들었습니다. 5개 retrieval tool (SQL, FTS5, SPARQL,
> Cypher, KPI) 을 만들어서 agent 가 질의 유형에 따라 라우팅합니다. 예를
> 들어 '냉각수 펌프 근처 배관 찾아줘' 는 Cypher 로 3-hop 인접 탐색 +
> Equipment 필터, 'Criticality 가 가장 높은 10개는?' 은 KPI tool + SQL
> 조합으로 처리합니다. 현재는 Gemini 2.5 Flash 를 쓰지만 LangGraph 의 모델
> 어댑터 추상화 덕분에 GPT·Claude·EXAONE·Llama 등 어떤 LLM 으로도 1줄
> 교체 가능합니다. 자체 LLM·온프레미스 환경에 즉시 transfer 가능한 모듈로
> 설계했습니다."

---

## 5. 역량 #4 — 데이터 분석 & 피처 엔지니어링

### # 구현 — 증명 산출물

- **Gold 테이블 219 cols** (`src/bimkg/ingest/exporters/foundry.py` Object Type all-in-one)
- **파생 피처 카탈로그** (Silver → Gold):

| 피처 | 로직 | 가치 |
|------|------|------|
| `length_m_si`, `mass_kg_si` | SP3D 문자열 → SI 단위 변환 (`unit_parser.py`, 44 tests) | 단위 혼재 → 정규화 (mm/inch/lb 모두 처리) |
| `classification_confidence` | HIGH / LOW / LIKELY_BUG 3-level | M1 발견 후 데이터 신뢰 신호 추가 |
| `classification_confidence_reason` | "regex word boundary 위반" 등 사유 | 다운스트림에서 LOW 추적 가능 |
| `adjacency_tier` | HIGH (정확) / MEDIUM (AABB 충돌 의심) / LOW (parent box) | M2 발견 후 정밀도 향상 |
| `is_parent_box` | SP3D parent container 여부 | M3 해결, 인접 그래프 66% 오염 제거 |
| `equipment_type_normalized` | 8 subclass mapping (Process/Electrical/HVAC/Civil/BlackBox 등) | downstream KPI 계산 기반 |

- **5 notebooks** `notebooks/` (EDA · Class Map · Spatial · Phase 1 verify · Confusion Matrix)
- **25 PNG figures** `notebooks/figures/` (DPI 300, 시각화 PNG 룰 준수)
- **pandas + SQL** 광범위 사용, **SQLite warehouse 7 tables / 62.9 MB**
- **ydata-profiling 리포트** 219 cols / 270 quality alerts / 25.4 MB HTML

### # 크로스역량 — 왜 채용 시장에서 중요한가

"데이터 분석 & 피처 엔지니어링" + "Pandas · SQL" 은 Data Analyst · Data
Scientist · ML Engineer 공고 필수 항목입니다. 단순 사용을 넘어 **"도메인
노이즈를 발견하고 피처로 흡수"** 하는 패턴이 핵심:

- M1 발견 → `classification_confidence` 컬럼 추가 (downstream 이 선택적으로 LOW 제외)
- M2 발견 → `adjacency_tier` 추가 (분석 정밀도 별 결과 분리)
- M3 발견 → `is_parent_box` flag (그래프 분석에서 노이즈 객체 제외)

이 패턴은 **"새 데이터 문제를 발견 → 즉시 피처로 흡수 → downstream 변경
없이 신호 전달"** 의 production-grade 데이터 엔지니어링 reflex 입니다.
센서 데이터 · 소비자 행동 데이터 · 금융 거래 데이터 등 **노이즈가 많은
모든 도메인** 에서 동일한 reflex 가 요구됩니다.

### 면접 언어

> "BIM 데이터에서 Piping 으로 분류된 4,014 객체 중 24.8% 가 실제로
> Structure 라는 걸 발견했습니다. 처음에는 분류기를 다시 짤까 고민했지만,
> 다운스트림 (PowerBI · Foundry · OWL) 이 이미 운영 중이라 컬럼만 추가해서
> 신호를 흘리는 방향을 택했습니다. classification_confidence (HIGH/LOW/
> LIKELY_BUG) 와 confidence_reason 두 컬럼을 추가해서, 다운스트림이
> 선택적으로 LOW 를 필터하거나 사용자에게 경고를 띄울 수 있게 했습니다.
> 같은 패턴을 M2 (adjacency_tier), M3 (is_parent_box) 에도 반복 적용해서,
> 새 발견을 즉시 피처로 흡수하는 reflex 를 dev-standards R3 (Finding
> Archive) 룰로 표준화했습니다."

---

## 6. 역량 #5 — 문제 정의 → 데이터 기반 해결 (E2E Ownership)

### # 문제해결 — 증명 산출물

3건의 finding 모두 **5단계 표준 프로세스** (R3 Finding Archive Rule) 적용:

> 발견 → audit.py 재현 → 시각화 → 결정 trace → 외부 PR 기여 (해당 시)

| Finding | 발견 | 증거 | 결정 | 외부 기여 |
|---------|------|------|------|-----------|
| **M1 — Piping 오분류** | 997 객체 (24.8%) 가 Structure 인데 Piping 분류 | `findings/2026-04-12-M1-piping-misclassification/` (audit + 4 figures + 5 CSV) | regex word boundary 적용 → Piping HIGH 2,926 / LIKELY_BUG 136 | **DXTnavis PR #3** (upstream 해결) |
| **M2 — Adjacency tier** | AABB 단일 거리는 정밀도 35.4% | `findings/2026-04-12-M2-adjacency-tiers/` | 3-tier 분류 (HIGH/MED/LOW) 도입 | 내부 해결 |
| **M3 — Parent Box 오염** | 448 SP3D parent container 가 인접의 66% 오염 | `findings/2026-04-13-M3-parent-box-contamination/` | `is_parent_box` flag + tier 재계산 | **DXTnavis Issue #2, #4** 제출 |

### # 크로스역량 — 왜 채용 시장에서 중요한가

"문제 해결 능력 및 논리적 사고" + "문제 정의 및 데이터 기반 해결 전략"
은 거의 모든 채용 공고의 필수·업무 항목입니다. 하지만 대부분의 후보자는
"이슈를 해결했다" 수준에서 멈추며, 채점자가 실제로 보려는 것은:

1. **발견 → 재현 → 시각화 → 근본 원인** 까지의 탐구 깊이
2. **외부 공급사·upstream 까지 추적** 해서 근본 해결하는 reflex
3. **5단계 프로세스를 룰로 표준화** 해서 팀 작업 방식으로 승격시키는 능력

이 3단계가 모두 갖춰진 사례는 드물며, 특히 **외부 데이터 공급사와의 협업
경험** (DXTnavis PR + Issue 제출) 은 외부 솔루션사·SI 업체와의 협업 일상
(엔터프라이즈 환경) 에 그대로 transfer 됩니다.

### 면접 언어

> "Phase 1 완료 후 데이터 품질 감사를 하다가 Piping 으로 분류된 객체 중
> 24.8% 가 실제로는 Structure 인 걸 발견했습니다. 원인을 추적해보니
> DXTnavis 의 InferClass 함수가 'tee' 키워드를 'steel' 의 substring 으로
> 매칭하고 있었습니다. 그냥 로컬에서 우회할 수도 있었지만 5단계 finding
> archive 프로세스를 적용했습니다 — audit.py 로 재현, 4개 figure 로
> 시각화, README 5섹션으로 분석, 그리고 DXTnavis 저장소에 PR #3 (regex
> word boundary 적용) 와 Issue #4 를 제출해서 upstream 까지 해결했습니다.
> 이 reflex 를 dev-standards R3 (Finding Archive Rule) 로 표준화해서 팀
> 작업 방식으로 승격시켰습니다."

---

## 7. ML/AI 엔지니어 일반 JD 매핑 템플릿

ML/AI 엔지니어 · Data Scientist · AI Engineer · MLOps · Backend 직군 공고에
자주 등장하는 키워드 vs 이 프로젝트의 증명:

### 7.1 필수·공통 항목

| JD 키워드 | 이 프로젝트의 증명 | 완성도 |
|-----------|--------------------|:------:|
| Python | 8K LOC Python (src/bimkg/ + scripts/ + notebooks/), 336 tests | ✅ 완성 |
| ML/DL 기본 개념 이해 | A/B testing (R10), KPI 통계 공식 4종, classification confidence 3-level, deep-dive §8 의 4 ML task 설계 | ✅ 완성 |
| 문제 해결 능력 및 논리적 사고 | M1/M2/M3 5단계 archive + R10 결정 trace + DXTnavis PR/Issue 기여 | ✅ 완성 |
| Pandas · SQL · 시각화 | pandas + SQLite 7 tables 62.9 MB + 5 notebooks + 25 PNGs + ydata-profiling | ✅ 완성 |

### 7.2 업무·경험 항목

| JD 키워드 | 이 프로젝트의 증명 | 완성도 |
|-----------|--------------------|:------:|
| 데이터 파이프라인 구축 및 최적화 | Medallion 4계층 + Airflow 7 tasks · 14 Assets + OpenLineage v2 + lineage impact 24 datasets | ✅ 완성 |
| API 및 백엔드 + AI 모델 연동 | FastAPI 12 endpoints + LangGraph 5-tool agent (LLM-agnostic) | ✅ 완성 |
| 실험 설계 및 결과 분석 (A/B 테스트) | dev-standards R10 자체 정립 + 3건 적용 | ✅ 완성 |
| 데이터 분석 및 피처 엔지니어링 | 219 Gold cols + 6 파생 피처 카탈로그 + 5 notebooks | ✅ 완성 |
| 문제 정의 + 데이터 기반 해결 전략 | M1/M2/M3 + DXTnavis PR #3 + Issues #2/#4 | ✅ 완성 |
| ML/DL 모델 서비스 배포 및 운영 (MLOps) | LLM agent 서빙 (FastAPI mount) + OpenLineage 추적 + SHACL 검증 게이트 + Foundry SDK 업로드 | 🟡 honest gap (직접 ML 모델 학습 · 서빙 경험은 미보유) |
| 모델 성능 모니터링 및 개선 | SHACL 6 shapes / 468 violations 자동 탐지 + classification_confidence proxy 신호 | ✅ 완성 (품질 게이트 기준) |
| ML/DL 모델 설계 및 개발 | classification confidence 3-level + AABB tier + KPI 33종 + deep-dive §8 의 4 ML task 설계 명세 | 🟡 honest gap (학습 단계 미수행) |

### 7.3 우대·전문 항목

| JD 키워드 | 이 프로젝트의 증명 | 완성도 |
|-----------|--------------------|:------:|
| TensorFlow / PyTorch | **사용 안 함** | ❌ |
| 클라우드 (AWS / GCP / Azure) | Palantir Foundry Cloud (10 datasets, dtype 호환 이슈 직접 해결) + Google AI Gemini API | 🟡 부분 (raw AWS/GCP 미사용) |
| 논문 구현 / 프로젝트 경험 | Louvain modularity, AABB intersection, OWL RL reasoning, 3-constraint precedence DAG + critical chain — 알고리즘 구현 4종 | ✅ 완성 |
| RDF / OWL / SPARQL / Knowledge Graph | 477K triples, 28 classes, rdflib SPARQL endpoint, LangGraph SPARQL tool | ✅ 완성 |
| SHACL / 데이터 품질 검증 | 6 shapes, 468 violations 자동 탐지 + severity 정책 | ✅ 완성 |
| Neo4j / Graph Database | 261K edges, 6 관계 타입, Cypher tool 연동 | ✅ 완성 |
| GraphRAG / LLM agent | LangGraph 5-tool ReAct agent | ✅ 완성 |
| FastAPI / Pydantic | 12 endpoints, Swagger, 336 tests | ✅ 완성 |
| Airflow / 워크플로 오케스트레이션 | Airflow 3.x 7 tasks · 14 Assets · dataset-aware scheduling | ✅ 완성 |
| OpenLineage / 데이터 lineage | v2 ColumnLineage facets 14 events | ✅ 완성 |
| Docker / 컨테이너 운영 | Neo4j Docker 재현 가능 설정 (`scripts/neo4j_import.sh`) | 🟡 부분 |
| CI/CD (GitHub Actions) | 미구축 | ❌ 없음 |
| 성능 튜닝 (QPS, p95 latency) | 측정 안 됨 | ❌ 없음 |

**총평**:
- **필수 4/4 ✅, 업무 8/8 매칭** (6 ✅ + 2 🟡 honest gap)
- **전문 항목 7 ✅ + 3 🟡 + 3 ❌** (TF/PyTorch · CI/CD · 성능 튜닝 부재)
- ML/AI · 데이터 · 백엔드 직군의 실무 업무 중심 평가에서 **방어 가능한
  mid-junior 수준** 자료

---

## 8. 솔직한 Gap — TF/PyTorch + 직접 DL 학습 미경험

### # 크로스역량 — Honest Framing

**현재 미경험**:
1. TensorFlow / PyTorch 직접 사용
2. 신경망 모델 학습 (loss curve, validation, hyperparameter tuning)
3. GPU 클러스터 운영
4. CI/CD 파이프라인 (GitHub Actions)
5. 성능 벤치마크 (QPS, p95 latency)

**보유 인접 역량으로 보완**:

| 인접 역량 | 보유 증거 | DL 학습 경험으로의 거리 |
|-----------|-----------|----------------------|
| 모델 서빙 인프라 | LLM agent 가 FastAPI 위에 mount, 응답 trace, 토큰 비용 측정 | 학습된 모델을 받아 서빙은 즉시 가능 |
| 데이터 파이프라인 | Medallion + Airflow + lineage 완비 | 학습 데이터 준비·버전 관리는 즉시 가능 |
| 검증 게이트 | SHACL + 자체 audit script + 336 tests | 모델 검증 메트릭 추가는 동일 패턴 |
| 알고리즘 이해 | Louvain · AABB · OWL RL · DAG 직접 구현 경험 | DL 알고리즘 학습 곡선 짧음 |

### # 구현 — 학습 로드맵 (지원 전 보완 후보)

**deep-dive §8 의 4 ML task** 가 이미 데이터·문제·평가 metric 까지 명세된
상태. PyTorch 로 구현하면 즉시 portfolio 에 추가 가능:

| Task | 학습 가능성 | PyTorch 구현 난이도 |
|------|------------|--------------------|
| **A. 미분류 객체 자동 분류** (LIKELY_BUG 136건 보정) | XGBoost / 간단한 MLP — text + 카테고리 피처 입력 | ⭐ 낮음 (~1주) |
| **B. 시공 시간 예측** | Tabular regression (Equipment + Pipeline 속성) | ⭐⭐ 중간 (~2주) |
| **C. 이상 탐지** (Statistical anomaly) | Isolation Forest 또는 Autoencoder | ⭐⭐ 중간 (~2주) |
| **D. GraphRAG 유사 설비 추천** | Node embedding (Node2Vec / GraphSAGE) | ⭐⭐⭐ 높음 (~3주, PyTorch Geometric 학습 포함) |

**추천 우선순위**: Task A → Task D (DL 모델 설계·학습 경험 + 기존 KG 자산
활용도 최대).

### 면접 언어

> "TensorFlow 나 PyTorch 로 직접 모델을 학습한 경험은 없습니다. 그래서
> deep-dive 문서 §8 에 명세해둔 4개 ML task 중 Task A (미분류 객체 자동
> 분류) 를 PyTorch 로 구현해서 portfolio 에 추가할 계획입니다. 데이터·
> 문제 정의·평가 metric 은 이미 갖춰져 있어서, DL 프레임워크 학습 곡선만
> 채우면 됩니다. 그동안 갖춘 모델 서빙 (FastAPI + LangGraph), 데이터
> 파이프라인 (Medallion + Airflow), 검증 게이트 (SHACL) 인프라가 있어서
> 학습된 모델을 production 에 올리는 것은 즉시 가능합니다."

---

## 9. 산업·도메인별 Transfer 패턴

이 프로젝트의 아키텍처는 **특정 도메인에 종속되지 않는 범용 패턴** 이며
다음 산업에 직접 transfer 가능합니다. 지원 회사의 사업 영역에 따라
§1.1 의 도메인 매칭 키워드를 조합해 사용:

### 9.1 Plant · 제조 (정유·화학·배터리·반도체·철강)

- **직접 매칭**: BIM 객체 온톨로지 → 공정 설비 디지털 트윈 그대로
- **핵심 강조**: §1.1 도메인 스케일 (12K 객체) + §5 피처 엔지니어링 (센서·MES 노이즈 흡수)
- **면접 포인트**: "정유시설 BIM 12K 객체 처리 경험이 plant 의 생산라인 데이터에 직접 transfer"

### 9.2 B2C · 소비재 · 유통

- **구조 매칭**: 28 OWL classes → **상품·SKU·성분·카테고리 지식그래프** 구조 동일
- **핵심 강조**: §3 A/B 테스트 (마케팅 실험 문화 직격) + §4 LLM 5-tool RAG (상품 검색 · 개인화 추천)
- **면접 포인트**: "복잡한 도메인 엔터티를 온톨로지 + LLM agent 로 통합하는 아키텍처가 B2C 의 상품·고객·캠페인 통합에 그대로 적용"

### 9.3 금융 · 보험

- **구조 매칭**: 261K Neo4j edges → **상품·계약·리스크 관계 그래프** 경험 transfer
- **핵심 강조**: §1.3 거버넌스 (재현성·lineage·감사 가능성) + §3 A/B (리스크 모델 검증)
- **면접 포인트**: "규제 환경의 재현성·감사 요구를 Medallion + lineage + SHACL 로 처음부터 설계"

### 9.4 의료 · 바이오

- **구조 매칭**: OWL 28 classes → **SNOMED · MeSH · Disease Ontology** 와 유사 패턴
- **핵심 강조**: §6 문제 정의 (데이터 품질 reflex) + §4 LLM (문헌 검색 · 환자 이력 RAG)
- **면접 포인트**: "의료 지식그래프 (질병·약물·유전자) 구조 설계 경험"

### 9.5 통신 · 모빌리티

- **구조 매칭**: 110K 공간 인접 관계 → **네트워크·경로 그래프** 알고리즘 transfer
- **핵심 강조**: §4 GraphRAG (자연어 네트워크 질의) + §2 대용량 파이프라인
- **면접 포인트**: "인접 그래프 + Cypher 경로 탐색 경험이 통신망 · 물류망에 직접 적용"

### 9.6 엔터프라이즈 SI · AX 컨설팅

- **구조 매칭**: dev-standards R1~R11 → **고객사별 도메인 온톨로지 구축 표준**
- **핵심 강조**: §6 E2E ownership (외부 협업 reflex) + §1.3 거버넌스
- **면접 포인트**: "고객사마다 다른 도메인을 온톨로지로 모델링하는 작업 표준을 자체 정립한 경험"

---

## 10. 한 줄 요약 (이력서·자기소개서용)

> **정유시설 SP3D 도면 12,009 객체를 OWL 온톨로지(28 classes, 477K triples)
> · Neo4j 그래프(261K edges) 로 모델링하고, FastAPI 12 endpoints + LangGraph
> ReAct 에이전트(5-tool RAG, LLM-agnostic)로 자연어 질의 채널을 단독 구현.
> Medallion 4계층 + OpenLineage v2 + SHACL 6 shapes 로 엔터프라이즈 거버넌스를
> 갖췄으며, 외부 데이터 공급사(DXTnavis)에 PR #3 + Issues #2/#4 기여로
> 997 건 데이터 결함을 근본 해결.**

이 한 단락이 ML/AI · 데이터 · 백엔드 직군 이력서 필터에서 다음 키워드를
전부 포함:
- **데이터 파이프라인** (Medallion · Airflow · OpenLineage)
- **AI 모델 + 백엔드 연동** (FastAPI · LangGraph · 5-tool RAG)
- **지식그래프 / RDF / OWL / SPARQL / Neo4j**
- **SHACL / 데이터 품질 게이트**
- **MLOps 인프라** (lineage · versioning · 검증 게이트)
- **A/B 테스트 / 실험 설계** (R10 dev-standards)
- **도메인 ownership** (DXTnavis PR + Issue 기여)
- **LLM 통합** (ReAct agent · tool-calling · GraphRAG)

---

## 11. 참조

- 코드 저장소: `/home/taegwan-dev/dev/first-ontology-project`
- 단일 포털: [`docs/PROJECT-JOURNAL.md`](../PROJECT-JOURNAL.md)
- DA/DS 심층 분석: [`data-analyst-data-scientist-deep-dive.md`](data-analyst-data-scientist-deep-dive.md) — 832줄 reference (11 섹션)
- KG 엔지니어 7가지 역량: [`ontology-kg-engineer-perspective.md`](ontology-kg-engineer-perspective.md) — 480줄
- R11 portfolio gap analysis: [`r11-portfolio-gap-analysis.md`](r11-portfolio-gap-analysis.md)
- LLM agent: [`src/bimkg/llm/`](../../src/bimkg/llm/)
- FastAPI: [`src/bimkg/api/main.py`](../../src/bimkg/api/main.py)
- Findings: [`docs/findings/`](../findings/)
- dev-standards (R1~R11): <https://github.com/tygwan/dev-standards>
- Notion portfolio (외부): <https://www.notion.so/Refinery-Facility-Ontology-Analytics-3405a4e1f87881d08fd4f9ed41234793>

---

*Last updated: 2026-04-14 (직무 역량 중립 버전, R11 v0.2.0 marker 적용, §9 산업별 transfer 패턴)*
