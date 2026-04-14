# AI FDE 옵션 설정 가이드

**대상**: Foundry AI FDE application
**목적**: Models / Skills / Documentation / Tools 4가지 옵션을 BIM-KG 프로젝트에 맞게 설정

---

## 📋 AI FDE 4가지 옵션 개념

AI FDE는 **커스텀 가능한 AI 에이전트**입니다. 이 4가지를 조합해 어떤 일을 할지 결정:

```
┌──────────────────────────────────────────────────────────┐
│ AI FDE = Models (뇌) + Skills (성격) + Docs (지식) + Tools (손) │
└──────────────────────────────────────────────────────────┘
         ↑           ↑          ↑              ↑
         추론       페르소나   RAG 참고자료    실행 능력
```

| 옵션 | 역할 | 비유 |
|---|---|---|
| **Models** | 추론 엔진 (LLM 선택) | "어떤 두뇌를 쓸까" |
| **Skills** | 워크플로우 템플릿 | "어떤 직무를 맡길까" |
| **Documentation** | RAG 참고자료 | "어떤 매뉴얼을 읽을까" |
| **Tools** | API/함수 실행 권한 | "무슨 일을 시킬까" |

---

## 1. Models (모델 선택)

AI FDE 뒤에 있는 LLM을 선택합니다. 작업 성격에 따라 다름:

| 모델 계열 | 장점 | BIM-KG에서 추천 상황 |
|---|---|---|
| **Claude Opus** (4 / 4.5) | 긴 컨텍스트(200K+), 깊은 추론, 코드 품질 | **Phase 1–2 (탐색/모델링)** — 219 컬럼 맥락 유지 필요 |
| **Claude Sonnet** (4 / 4.6) | Opus 대비 3–5배 빠름, 거의 동등한 품질 | **Phase 3 (고도화 반복)** — 빠른 iteration |
| **GPT-4o / GPT-5** | 일반 목적, 도구 호출 잘함 | Agent 프로토타이핑 |
| **Gemini** | 이미지 이해 탁월 | 3D 스크린샷 분석 시 |

### 권장 설정
```
Primary model: Claude Sonnet 4.6 (or Opus 4.6 if available)
Fallback:     GPT-4o
Long-context task: Opus 4.6 (1M context if available)
```

### 왜 Claude 계열인가
- BIM Ontology는 **구조화된 추론**이 중요 (Claude가 상대적으로 강함)
- 한국어 domain 용어가 섞여 있음 (Claude 한국어 품질 좋음)
- 219 컬럼 / 10+ 데이터셋 맥락을 놓치지 않아야 함 (long-context)

---

## 2. Skills (스킬 / 페르소나)

Skills는 **사전 정의된 워크플로우 + 시스템 프롬프트 묶음**. 주요 카테고리:

| Skill 유형 | 설명 | BIM-KG 활용 |
|---|---|---|
| **Data Engineer** | ETL, 스키마 설계, SQL | Phase 1, 2에 핵심 |
| **Ontology Modeler** | Object Type / Link 설계 | Phase 2에 필수 |
| **Analytics / KPI** | 지표 개발, 통계 분석 | Phase 3, 5 |
| **Code Generator** | TypeScript/Python 함수 | Phase 6 (Functions) |
| **Documentation Writer** | 사용자 문서 / 주석 | 마지막 단계 |
| **Conversational Agent** | 최종 사용자용 대화 UX | Phase 4 (AIP Agent 설계) |

### Phase별 추천 Skill 조합

```
Phase 1 (탐색):
  ✓ Data Engineer
  ✓ (선택) Domain Expert — BIM/SP3D 지식

Phase 2 (모델링):
  ✓ Data Engineer
  ✓ Ontology Modeler

Phase 3 (고도화):
  ✓ Analytics / KPI
  ✓ Code Generator

Phase 4 (Agent 설계):
  ✓ Conversational Agent
  ✓ Ontology Modeler
```

### Skill 선택 시 주의
- Skill을 너무 많이 켜면 system prompt가 길어져 응답 품질 하락
- **한 세션에 2–3개만** 활성화 권장

---

## 3. Documentation (참고자료)

AI FDE가 RAG로 검색할 수 있는 문서 모음. **우리 프로젝트의 강점은 바로 이것**.

### BIM-KG에서 필수로 attach할 문서

**레벨 A — 맥락 이해용 (필수)**:
1. `docs/PROJECT-JOURNAL.md` — 프로젝트 전체 portal
2. `docs/plan/foundry-next-steps-roadmap.md` — 현재 로드맵
3. `docs/reference/fbx-mapping-numerical-analysis.md` — 최근 분석 결과
4. `docs/analysis/foundry-dataset-profiles-YYYY-MM-DD.md` — SDK 자동 생성 (준비 중)

**레벨 B — 도메인 지식 (중요)**:
5. `docs/findings/2026-04-15-M4-fbx-guid-mapping/README.md` — 최신 finding
6. `docs/findings/2026-04-12-M2-adjacency-tiers/README.md` — Adjacency 분류
7. `docs/findings/2026-04-13-M3-parent-box-contamination/README.md` — 데이터 품질

**레벨 C — 설계 결정 (참고)**:
8. `docs/plan/pipeline-implementation-plan.md` — 전체 설계
9. `docs/reference/foundry-setup-guide.md` — Foundry 이전 설정 이슈

### 문서 업로드 팁
- AI FDE는 통상 **여러 파일 합산 제한** (예: 20MB, 50페이지) 있음
- M1~M3는 굳이 올리지 말고, **M4만** (최신이자 가장 임팩트 큼)
- PROJECT-JOURNAL은 반드시 포함 (프로젝트 네비게이션 문서)

### 잘못된 선택 (흔한 실수)
- ❌ `notebooks/*.ipynb` 통째로 업로드 (JSON이라 노이즈 많음)
- ❌ `data/` 디렉토리 (Foundry가 이미 스키마 접근 가능)
- ❌ `.venv/` 의존성 파일들

---

## 4. Tools (도구 / 함수 실행)

AI FDE가 호출할 수 있는 **실행 가능한 액션**.

### 기본 내장 Tools (Foundry 제공)

| Tool | 기능 | Phase별 활용 |
|---|---|---|
| **Dataset Reader** | Parquet/CSV 내용 조회 | 모든 Phase |
| **SQL Executor** | Spark SQL 실행 | Phase 1, 3 |
| **Ontology Query** | Object Type search/filter | Phase 2+ (등록 후) |
| **Code Sandbox** | Python/TypeScript 실행 | Phase 3 |
| **Chart Builder** | Quiver 차트 생성 | Phase 5 |

### BIM-KG에서 권장 조합

**Phase 1 (탐색)**:
```
✓ Dataset Reader (필수)
✓ SQL Executor (aggregate 확인용)
✓ (있으면) Chart Builder
```

**Phase 2 (모델링)**:
```
✓ Dataset Reader
✓ Ontology Query (current state 확인)
✓ Code Sandbox (Python으로 cross-dataset 검증)
```

**Phase 3+ (고도화)**:
```
✓ Ontology Query
✓ Code Sandbox
✓ Function Executor (우리가 배포한 Function 호출)
```

### Custom Tools (우리 프로젝트 전용)

Phase 5 LLM agent에 있던 5 tools를 **Foundry Function으로 이식**하면 AI FDE가 직접 호출 가능:

```typescript
// 후속 작업 후보
Function.calculate_pipeline_isolation(pipeline_id)
Function.zone_shutdown_impact(zone_id)
Function.critical_path_for_class(class_name)
```

---

## 5. 통합 추천 설정표

### Phase 1 세션 (데이터 탐색)
```yaml
Model:    Claude Sonnet 4.6
Skills:   Data Engineer, Ontology Modeler
Docs:
  - PROJECT-JOURNAL.md
  - foundry-next-steps-roadmap.md
  - foundry-dataset-profiles-YYYY-MM-DD.md (SDK 자동 생성)
  - M4 finding README
Tools:    Dataset Reader, SQL Executor, Code Sandbox
```

### Phase 2 세션 (Ontology 모델링)
```yaml
Model:    Claude Opus (long-context)
Skills:   Ontology Modeler, Data Engineer
Docs:
  - Phase 1 session 결과 메모
  - foundry-dataset-profiles
  - fbx-mapping-numerical-analysis.md
Tools:    Ontology Query, Dataset Reader
```

### Phase 3 세션 (고도화)
```yaml
Model:    Claude Sonnet 4.6 (빠른 iteration)
Skills:   Analytics/KPI, Code Generator
Docs:
  - Phase 2 Ontology 설계
  - M2/M4 findings (KPI 계산 맥락)
Tools:    Code Sandbox, Ontology Query, Function Executor
```

---

## 6. 세션 진행 시 팁

### DO
- ✅ **한 세션에 한 Phase**만 — 맥락 혼선 방지
- ✅ 각 세션 시작 시 **"이전 세션 요약" 문서를 upload**
- ✅ AI FDE의 질문에 **역으로 대답**해서 context를 refine
- ✅ 중요한 결론은 **바로 markdown으로 저장** (`docs/analysis/ai-fde-sessions/`)

### DON'T
- ❌ 너무 많은 skill 동시 활성화 (system prompt 폭주)
- ❌ 219 컬럼 전체를 한 번에 분석 요구 (단계적으로)
- ❌ "자유롭게 탐색해봐" 같은 모호한 요청 (구체 질문)
- ❌ 이미 해결된 M1–M4를 재검토 요청 (시간 낭비)

---

## 7. 다음 단계

이 가이드를 읽고 AI FDE 설정을 마쳤다면, 순서대로:

1. `01-phase1-exploration.md` — 탐색 세션 스크립트
2. `02-phase2-modeling.md` — Ontology 설계 세션
3. `03-phase3-advancement.md` — 고도화 / Function 설계

각 파일은 **AI FDE에 복사-붙여넣기 가능한 프롬프트** 형태로 제공됩니다.
