# Phase 5 설계 — LLM/GraphRAG 자연어 BIM 질의

> BIM 데이터에 자연어로 질문하고, 적절한 데이터 소스 (SQL, SPARQL, Cypher) 를
> 자동 선택하여 답변하는 multi-tool agent 를 구축합니다.

---

## 1. 문제 정의

12,009 BIM 객체 × 218 컬럼의 데이터가 4개 저장소 (SQLite, OWL/TTL, Neo4j, Parquet) 에
분산되어 있음. 사용자가 "P-10147 파이프라인의 총 중량은?" 이라고 물으면:
- 어떤 저장소에서 찾아야 하는지 판단해야 하고 (SQL? SPARQL? Cypher?)
- 적절한 쿼리를 생성해야 하고
- 결과를 BIM 도메인 맥락에서 해석해야 함

수동으로 하면 SQL/SPARQL/Cypher 각각 알아야 하고, 매번 쿼리를 작성해야 함.

## 2. 질의 유형 분류

| 유형 | 예시 | retrieval 소스 | 도구 |
|------|------|---------------|------|
| **집계** | "Piping 몇 개?", "총 중량?" | SQL COUNT/SUM | SQLite |
| **검색** | "P-10147 에 뭐가 있어?" | SQL WHERE | SQLite |
| **텍스트 검색** | "Valve 라는 이름의 객체?" | FTS5 | SQLite |
| **관계 탐색** | "이 장비 주변에 뭐가 있어?" | graph traversal | Neo4j Cypher |
| **시맨틱** | "파이프라인에 속하지 않은 PipingComponent?" | SPARQL pattern | OWL/rdflib |
| **시공 추론** | "이 장비 설치 전에 뭘 먼저?" | DAG traversal | Neo4j MUST_PRECEDE |
| **KPI 조회** | "가장 시공 어려운 존?" | 복합 (SQL + analytics) | SQLite + kpi.py |

## 3. 아키텍처

```
사용자 질의 (자연어)
       │
       ▼
┌─────────────────┐
│  LangChain Agent │  ← system prompt (BIM 도메인 컨텍스트)
│  (Claude Sonnet) │  ← few-shot examples (5개 대표 질의)
└───────┬─────────┘
        │ tool selection
        ▼
┌───────────────────────────────────────┐
│  Tools                                 │
│  ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │sql_query │ │sparql    │ │cypher  ││
│  │(SQLite)  │ │(rdflib)  │ │(Neo4j) ││
│  └──────────┘ └──────────┘ └────────┘│
│  ┌──────────┐ ┌──────────┐           │
│  │text_search│ │kpi_lookup│           │
│  │(FTS5)    │ │(pandas)  │           │
│  └──────────┘ └──────────┘           │
└───────────────────────────────────────┘
        │ query results
        ▼
┌─────────────────┐
│  Agent response  │  ← 결과 해석 + 도메인 맥락 + 소스 인용
└─────────────────┘
```

## 4. 설계 결정

### D12 — LangChain agent 채택 (Option B)

**맥락**: 3가지 옵션 검토
- A: Claude API 직접 + tool use → 의존성 최소, 커스터마이징 자유
- B: LangChain agent + tools → agent loop/memory 기본 제공, JD 요구 기술
- C: LlamaIndex KG index → KG-native, 하지만 커스텀 제한

**결정**: Option B (LangChain)

**근거**:
1. JD 에 LangChain 명시적 요구 → 경험 획득 가치
2. multi-tool agent 가 5개 도구를 오케스트레이션하는 우리 유스케이스에 정확히 맞음
3. 나중에 LlamaIndex 로 확장하거나, 직접 구현으로 교체할 수 있음 (비배타적)

### D13 — 5개 retrieval tool 구성

| Tool | 입력 | 출력 | 소스 |
|------|------|------|------|
| `sql_query` | SQL 문자열 | DataFrame → JSON | SQLite bimkg.db |
| `text_search` | 검색어 | 매칭 객체 목록 | SQLite FTS5 |
| `sparql_query` | SPARQL 문자열 | bindings → JSON | rdflib in-memory |
| `cypher_query` | Cypher 문자열 | records → JSON | Neo4j bolt |
| `kpi_summary` | zone_id 또는 pipeline | KPI dict | pandas kpi.py |

### D14 — System prompt 구성

3 파트:
1. **도메인 컨텍스트**: "이 데이터는 SP3D 플랜트 BIM 모델 12,009 객체..."
2. **도구 안내**: 각 tool 의 용도와 스키마 (테이블 컬럼, OWL 클래스, Neo4j 관계 등)
3. **few-shot examples**: 5개 대표 질의 → tool 선택 → 응답 패턴

## 5. 구현 단계

| 단계 | 모듈 | 내용 | 의존성 |
|------|------|------|--------|
| **5a** | `src/bimkg/llm/tools.py` | 5개 tool 함수 (SQLite, FTS5, SPARQL, Cypher, KPI) | SQLite, rdflib, neo4j driver |
| **5b** | `src/bimkg/llm/prompts.py` | system prompt + few-shot examples + 도메인 용어집 | tools.py 스키마 |
| **5c** | `src/bimkg/llm/agent.py` | LangChain Agent 구성 + tool 등록 + 대화 인터페이스 | langchain, tools, prompts |
| **5d** | SQLite FTS5 | `bim_objects_fts` 테이블 생성 (display_name, pipeline, system_path) | SQLite |
| **5e** | `tests/test_llm/` | mock API + 5개 golden answer 검증 | agent.py |

## 6. 예상 질의와 응답

### 6.1 집계형
```
Q: "P-10147 파이프라인의 총 중량과 부품 구성은?"
Tool: sql_query → SELECT refined_class, count(*), sum(dry_weight_kg) 
      FROM bim_objects WHERE sp3d_pipeline = 'P-10147' GROUP BY refined_class
A: "P-10147 에는 129개 배관 부품, 총 건조 중량 1,684 kg 입니다."
```

### 6.2 관계 탐색형
```
Q: "Equipment 'Aspects' 주변에 뭐가 있어?"
Tool: cypher_query → MATCH (e:BIMObject {displayName: 'Aspects'})-[:ADJACENT_TO]-(n)
      RETURN n.displayName, n.refinedClass LIMIT 20
A: "Aspects 주변에 Structure 12개, Piping 5개, Equipment 2개가 인접해 있습니다."
```

### 6.3 시공 추론형
```
Q: "가장 시공이 어려운 존은 어디야?"
Tool: kpi_summary → zone_kpis sorted by (weight × density / accessibility)
A: "Zone 0 이 가장 시공 난이도가 높습니다 (477 객체, 186t, 접근성 0.02)."
```

### 6.4 시맨틱형
```
Q: "파이프라인에 속하지 않은 배관 부품이 있어?"
Tool: sparql_query → SELECT ?s WHERE { ?s a bim:PipingComponent . 
      FILTER NOT EXISTS { ?s bim:belongsToPipeline ?p } }
A: "68개의 PipingComponent 가 파이프라인에 소속되지 않았습니다. (SHACL 검증 결과와 일치)"
```

### 6.5 텍스트 검색형
```
Q: "이름에 'Blind' 가 포함된 객체를 찾아줘"
Tool: text_search → FTS5 MATCH 'Blind'
A: "42개 객체가 발견되었습니다: Blind Flange (22개), Blind flange (20개)..."
```

## 7. 테스트 전략

| 테스트 유형 | 내용 | API 호출 |
|-----------|------|:--------:|
| **Unit: tool 함수** | SQL/SPARQL/Cypher 가 정확한 결과 리턴 | 없음 |
| **Unit: prompt 생성** | system prompt 에 스키마 정보 포함 확인 | 없음 |
| **Integration: golden answers** | 5개 질의에 대해 tool 선택 + 응답 정확도 | Mock |
| **E2E (수동)** | 실제 Claude API 호출 + 대화형 검증 | 실제 |

## 8. 리스크

| 리스크 | 대응 |
|--------|------|
| Neo4j 가 Docker 로 실행 중이어야 함 | tool 에서 연결 실패 시 graceful fallback + 메시지 |
| SPARQL 로드 15초 (477K triples) | agent 초기화 시 한 번만 로드, 캐싱 |
| LLM 이 잘못된 SQL/Cypher 생성 | 에러 catch → agent 에게 에러 메시지 전달 → 재시도 |
| API 비용 | claude-sonnet 사용 (opus 대비 10x 저렴), 토큰 제한 |

## 9. 의존성

```bash
# 추가 설치 필요
uv pip install langchain langchain-anthropic langchain-community neo4j
```

---

*이 설계 문서는 Phase 5 구현 착수 전에 작성되었습니다.*
*Last updated: 2026-04-13*
