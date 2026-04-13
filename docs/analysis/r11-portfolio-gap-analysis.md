# R11 Portfolio Writing — Gap Analysis & Application Plan

> dev-standards v0.3.0 의 신규 규칙 R11 (Portfolio / External Writing) 을
> 본 프로젝트의 portfolio 자료에 적용하기 위한 갭 분석.
>
> R11 원문: <https://github.com/tygwan/dev-standards/blob/main/rules/R11-portfolio-writing.md>

---

## 1. R11 적용 대상

R11 은 **외부 청자** 를 대상으로 하는 글에만 적용 (🟢 MAY).

| 자료 | 청자 | R11 적용 여부 |
|------|------|:-:|
| `portfolio/architecture-diagrams.html` | 외부 (recruiter / hiring manager) | ✅ 적용 대상 |
| `README.md` (예정) | GitHub 방문자 / 외부 | ✅ 적용 대상 |
| Notion / 개인 사이트 (예정) | 채용 / 공개 | ✅ 적용 대상 |
| `docs/PROJECT-JOURNAL.md` | 내부 | ❌ R1 영역 |
| `docs/tasklog/*` | 내부 | ❌ R2 영역 |
| `docs/findings/*` | 내부 | ❌ R3 영역 |
| `docs/analysis/*` | 내부 (기술 분석) | ❌ — 단, R11 은 이 자료를 입력으로 활용 |

R11 은 R1–R10 의 출력을 **외부용으로 재구성** 하는 규칙. 내부 문서를 외부로
복사-붙여넣기는 R11 anti-pattern.

---

## 2. 현재 portfolio HTML 갭 분석

`portfolio/architecture-diagrams.html` (1338 lines, 8 sections) 검토 결과:

### 2.1 위반 항목

| 항목 | 현 상태 | R11 요구 | 심각도 |
|------|---------|---------|:-:|
| **Arrow notation in prose** | `&rarr;` 가 본문 곳곳 ("135 → 175 cols", "Bronze → Silver → Gold") | 완전한 문장 사용. 화살표는 다이어그램에만 | 🔴 |
| **Tech-list 형식 카드** | "config.py / pyproject.toml / uv environment" 같은 stack 나열 | task 중심 ("환경 구성을 통해 X 가 가능해졌다") | 🔴 |
| **PAAR 구조 부재** | "Page 1 / Page 2..." 체계 — Problem-Analyze-Action-Result 가 없음 | 모든 major section 이 PAAR 4질문에 답해야 | 🔴 |
| **2-part narrative 부재** | Context/Value 와 Implementation 분리 없음 | Part 1 (도메인 + 문제 + 접근/결과) + Part 2 (아키텍처/엔지니어링/품질) | 🔴 |
| **Tech stack role-based 분류 없음** | "Data Processing: pandas, pyarrow, openpyxl, sqlite3, numpy" — role 미명시 | `{ name, role }` 형식: "pandas — Medallion 데이터 변환 + 219 컬럼 enrichment" | 🟡 |
| **Operational Experience 미포함** | 운영/장애/최적화 사례 없음 | Foundry pandas 2.x dtype 호환 이슈 같은 운영 경험 추가 | 🟡 |
| **Open Source Contribution 미반영** | DXTnavis PR #3 가 portfolio 에 명확히 안 보임 | "PR #3 로 negative lookahead regex fix 제출, 997건 piping 오분류 해결" 형식 | 🟡 |
| **Generic numbered headings** | "Page 1 / Page 2..." | 콘텐츠를 반영하는 자연스러운 heading | 🟢 |

### 2.2 잘 된 항목

| 항목 | 평가 |
|------|------|
| Visual Asset Checklist | ✅ Architecture diagram, Chart/Table, Data Flow, Graph network 모두 포함 — R11 minimum 1개 충족 |
| Specific metrics | ✅ "12,009 objects", "477K triples", "336 tests", "144 zones" 등 구체 수치 |
| Active voice | 일부만 (HTML 카드 형식이라 voice 측정 어려움) |
| Domain grounding | △ 일부 — "SP3D BIM" 정도만 있고 정유 플랜트 도메인 설명 부족 |

---

## 3. 적용 계획

R11 은 MAY 이지만 portfolio 가 외부 채용/공개 용도라면 적용 가치가 큼.
다음 3단계로 진행 권장.

### Phase A — 신규 portfolio MD 작성 (가장 큰 효과)

R11 본문의 PAAR + 2-part narrative 형식을 그대로 따른 신규 자료:

```
portfolio/
├── README.md                       (NEW — R11 형식 main entry)
├── architecture-diagrams.html      (existing — visual aid 로 활용)
└── case-study-bim-kg.md            (NEW — R11 형식 case study)
```

`portfolio/README.md` 골격 예시:

```markdown
# BIM Knowledge Graph Pipeline

## 도메인과 문제                            <- Part 1 §1
정유 플랜트의 SP3D BIM 모델은 12,009개 객체와 110,173개 공간관계로
구성되는데, 시공 순서를 자동 분석하거나 자연어로 설계를 질의할 수 없었다.

## 접근과 결과                              <- Part 1 §2
온톨로지 기반 지식그래프로 변환하면 SPARQL 질의, Neo4j 경로 탐색, LLM
에이전트 검색이 한 모델에서 가능해질 것이라 판단했고, 477K RDF 트리플과
261K Neo4j 엣지를 생성하여 33개 KPI와 12개 REST 엔드포인트로 노출했다.

![Pipeline overview](../docs/reference/lineage/2026-04-12/lineage-graph.png)

---

## 아키텍처 결정                            <- Part 2 §1
Medallion Architecture를 택한 이유는 각 단계를 독립적으로 테스트하고
롤백할 수 있기 때문이다. ...

## 핵심 엔지니어링                          <- Part 2 §2
DXTnavis의 InferClass 함수가 word boundary 없는 substring matching을
사용하여 Piping 항목 997건을 오분류하고 있었다. negative lookahead
regex로 fix 를 작성하고 업스트림 PR #3 로 제출했다. ...

## 품질 보증                                <- Part 2 §3
336 tests / 23 files, Oracle 100% agreement (XLSX classifier),
SHACL 6 shapes 검증, A/B 검증 (AABB vs Producer adjacency: 35.4% precision 격차).

---

## 운영 경험                                <- Enrichment §1
**문제**: Foundry SDK upload 시 pandas 2.x str dtype 비호환 (3가지 패턴)
**원인**: pandas 2.x 가 future.infer_string=True 를 기본값으로 도입
**해결**: 모듈 최상단 pd.set_option("future.infer_string", False) +
         Int64 → float64 캐스팅 + all-null object 컬럼 빈 문자열 충전
**결과**: 10개 데이터셋 업로드 성공 (12K 객체 × 219 컬럼)
**예방**: foundry-dtype-compatibility.md 에 패턴 문서화

## 오픈소스 기여                            <- Enrichment §2
**대상**: DXTnavis (private repo, PR #3)
**문제**: substring matching 으로 "Pipe Rack" 안의 "pipe" 가 Piping 으로 분류
**기여**: negative lookahead regex (`pipe(?!\\s*(?:rack|trench|...))`)
**결과**: 997 건 오분류 해결, 분류 정확도 94.3% → 99.5%

## Tech Stack (role-based)                  <- R11 형식
- Python — Medallion 파이프라인 (Bronze/Silver/Gold) + 219 컬럼 enrichment
- rdflib — OWL TBox/ABox 직렬화 (477K triples)
- pyshacl — 6 shapes 검증 게이트
- networkx — Louvain community + Precedence DAG (18,214 edges)
- Apache Airflow 3.x — 7 tasks DAG, OpenLineage 통합
- ydata-profiling — Gold 테이블 자동 프로파일 (270 alerts)
- Palantir Foundry — Object Type 6개 백킹, 10 datasets
- FastAPI — 12 REST endpoints + Swagger
- Gemini 2.5 Flash — ReAct agent + 5 retrieval tools (SQL/FTS5/SPARQL/Cypher/KPI)
```

### Phase B — 기존 HTML 의 R11 개선 (3 high-priority 만)

전면 재작성 대신 critical 항목만 우선 수정:

1. **Arrow notation 제거**: HTML body 의 `&rarr;` 를 완전한 문장으로 교체
   (다이어그램 SVG 안의 화살표는 R11 anti-pattern 아님 — 시각 자료니까)
2. **Page 2/3/8 의 tech-list 카드**: card-text 에 task/role 한 줄 추가
3. **상단에 PAAR 요약 박스 추가**: 8 페이지 전체를 1 문단으로 요약 (Part 1 §1 + Part 1 §3)

### Phase C — 운영 경험 + 오픈소스 기여 section 추가

기존 HTML 의 "Page 7 Data Quality Findings" 다음에 두 section 추가:

- "Operational Experience" — Foundry pandas 호환 이슈 + 해결 + 예방
- "Open Source Contribution" — DXTnavis PR #3 (regex fix)

이 두 section 은 R11 의 "Enrichment Sections" 권장 항목으로, 운영 성숙도와
ecosystem awareness 의 강력한 시그널.

---

## 4. R11 X R10 X R4 시너지

R11 본문이 명시한 통합:

| Source rule | Portfolio 에서의 활용 |
|-------------|----------------------|
| **R1** (Documentation Architecture) | `PROJECT-JOURNAL.md` Timeline 이 portfolio Result section 의 raw material |
| **R4** (Decision Records) | D1–D9 결정 기록이 Part 2 §1 "아키텍처 결정" 의 근거 |
| **R10** (Decision Validation) | A/B 결과가 Part 2 §3 "품질 보증" 의 정량 근거 — AABB vs Producer (35.4% precision) |

**예**: `D1 Medallion architecture` 결정 기록 + 그 근거가 R11 portfolio 의
"왜 Medallion 인가" 문단으로 자연스럽게 흘러감.

---

## 5. 적용 우선순위

| Phase | 작업량 | 효과 | 권장 순서 |
|-------|-------:|-----:|:-:|
| A — 신규 portfolio MD 작성 | M (4-6시간) | 🔴 High — recruiter 의 첫 인상 결정 | 1순위 |
| B — 기존 HTML 의 R11 개선 (3 항목만) | S (1-2시간) | 🟡 Medium — 기존 자료의 즉시 개선 | 2순위 |
| C — Operational + Open Source section 추가 | S (1시간) | 🟡 Medium — high-signal differentiator | 3순위 |

전체 portfolio 재작성보다는 **A 먼저** 진행. R11 형식의 완성도 높은 단일
자료가 부분 개선된 8-page HTML 보다 외부 청자에게 강함.

---

## 6. 검토 체크리스트 (Phase A 완료 후)

R11 본문의 핵심 체크리스트를 그대로 사용:

- [ ] PAAR 4 질문에 모두 답함 (Problem / Analyze / Action / Result)
- [ ] Part 1 (Context/Value) + Part 2 (Implementation) 구조
- [ ] Tech stack 을 제거해도 핵심 스토리 성립 (Task over Tech)
- [ ] Visual Asset 1개 이상 포함 (Architecture diagram, Chart, Data flow 등)
- [ ] Tech stack 이 `{ name, role }` 형식
- [ ] 화살표 표기 (`→`) 가 본문 prose 에 없음
- [ ] 모든 주장에 구체 metric 동반
- [ ] Operational Experience 또는 Open Source Contribution 1개 이상 포함

---

## 7. 다음 단계 (별도 작업)

이 갭 분석은 적용 계획서. 실제 작업은 다음 세션에 사용자 의사 확인 후 진행:

1. **Phase A**: `portfolio/README.md` 작성 (R11 형식)
2. **Phase B**: `portfolio/architecture-diagrams.html` 의 3 high-priority 항목 수정
3. **Phase C**: HTML 또는 MD 에 Operational + Open Source section 추가
4. **검증**: 위 §6 체크리스트로 self-review

---

*Last updated: 2026-04-14*
