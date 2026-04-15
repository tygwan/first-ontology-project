# LG AX 직무 매칭 문서 작성

**일자**: 2026-04-14
**담당 Task**: 신규 (사용자 요청 — LG AX JD 분석 후 강점 매핑)
**커밋**: (pending)

---

## 1. 언어 / 내용

LG 그룹 AX (AI Transformation) 직무 채용 공고를 받아, Refinery 프로젝트의
산출물 중 강점이 될 항목을 선별하고 PAAR + 면접 언어 + JD 매칭표 형식의
직무 적합성 문서를 신규 작성.

| # | 산출물 | 입력 | 출력 |
|:-:|--------|------|------|
| 1 | `docs/analysis/lg-ax-job-fit.md` | LG AX JD (필수 4 + 우대 5 + 업무 8 항목) + 기존 deep-dive·KG perspective doc | 11 섹션 / 5 PAAR / JD 매핑 3표 / LG 5계열사 강조표 |

### 1.1 신규/수정 파일

```
docs/analysis/
└── lg-ax-job-fit.md                       # NEW (~410 lines)

docs/tasklog/
└── lg-ax-job-fit-doc-20260414.md          # NEW (이 파일)

docs/PROJECT-JOURNAL.md                     # MODIFIED (Timeline + Where-to-find)
```

---

## 2. 문제

**상황**:
- 사용자가 LG AX 직무 JD 를 제공 (필수 4 + 우대 5 + 업무 8 항목)
- 기존 portfolio 자료 (KG perspective + DA/DS deep-dive + R11 portfolio) 는
  있지만 **LG 그룹 + AX 직무 컨텍스트로 재정렬된 매핑 문서가 없음**
- Notion 본문에는 KG 엔지니어 7역량 단독 섹션은 있으나 ML/AI 엔지니어
  관점 단독 섹션은 부재

**구체 요구**:
1. JD 항목별 매칭 강도 분석 (필수/우대/업무)
2. 없는 역량 (TF/PyTorch, DL 학습) 에 대한 honest framing
3. LG 대기업 톤 (스타트업 톤 X)
4. AX 직무 컨텍스트 — EXAONE swap, plant 도메인, 엔터프라이즈 거버넌스
5. **안전한 방식** = doc 먼저 작성 후 검토 → Notion 반영 (사용자 명시 선택)

---

## 3. 분석

### 3.1 강점 랭킹 (LG AX 컨텍스트 적용 전)

JD 항목별 매칭 평가 결과:

- **TIER 1 (직격)**: 데이터 파이프라인 / A/B 테스트 / API+AI 연동 /
  데이터분석·피처 / 문제정의·해결 → **5개**
- **TIER 2 (부분, framing 필요)**: MLOps / 클라우드 / 알고리즘 구현 → **3개**
- **TIER 3 (침묵 권장)**: TF/PyTorch / 직접 DL 학습 → **2개**

### 3.2 LG 컨텍스트 적용으로 변동된 강점

- **도메인 매칭** 이 신규 1순위로 부상 (Refinery = 정유 plant ↔ LG화학·
  LG에너지솔루션·LG전자 스마트팩토리 인접)
- **EXAONE swap-ready** framing 이 LG AI Research·LG CNS·LG U+ 모두에
  공통 어필 포인트 (자체 LLM 활용 정책)
- **엔터프라이즈 거버넌스** (Medallion + lineage + SHACL + R1~R11 표준)
  이 대기업 협업 환경에서 핵심 평가 항목

### 3.3 honest gap framing 전략

R11 v0.2.0 의 "depth as authenticity" 원칙 적용:
- TF/PyTorch 는 **침묵하지 않고 명시**, 단 보유 인접 역량 (서빙·파이프라인·
  검증) 으로 **학습된 모델 production 화는 즉시 가능** 으로 framing
- deep-dive §8 의 4 ML task 가 이미 데이터·문제·metric 명세된 상태이므로
  **"입사 전 Task A (PyTorch MLP) 구현해서 portfolio 추가" 학습 로드맵** 으로 전환

---

## 4. 해결

### 4.1 문서 구조 결정

`ontology-kg-engineer-perspective.md` (480줄, 7가지 역량) 패턴을 미러링:

```
0. 한눈에 보기 (요약 표 + 한 줄 결론)
1. 핵심 차별점 — LG AX 직격 3가지 (도메인 / EXAONE swap / 거버넌스)
2~6. 5개 강점 축 (PAAR 형식: 증명 → 왜 중요 → 면접 언어)
7. JD 키워드 매핑표 (필수 4/4, 우대 3/5, 업무 8/8)
8. 솔직한 gap + 학습 로드맵
9. LG 5 계열사별 강조 우선순위 (LG AI Research / LG CNS AX / LG U+ AX /
   LG화학·LG에너지솔루션 / LG전자)
10. 한 줄 요약 (이력서/자기소개서용, 일반 + 도메인강조 2버전)
11. 참조
```

### 4.2 R11 single-source marker 적용

섹션 헤더에 `# 문제해결` / `# 구현` / `# 크로스역량` 마커 적용:
- `# 크로스역량`: 핵심 차별점, 한 줄 결론, 매칭 가치 설명
- `# 구현`: 증명 산출물, 학습 로드맵
- `# 문제해결`: M1/M2/M3 finding 섹션

이력서 view / portfolio view 자동 렌더링에 활용 가능.

### 4.3 LG AX 톤 조정

| Before (일반) | After (LG AX) |
|---|---|
| "5 tool LLM agent 구현" | "**모델 swap 가능** 5-tool retrieval — EXAONE 교체 1줄" |
| "Medallion 파이프라인" | "**재현성·거버넌스** 중심 4계층 (스냅샷 pin + lineage trace)" |
| "A/B 3건 비교" | "**의사결정 검증 표준 (R10)** + 3건 적용" |
| "오픈소스 PR 기여" | "**외부 데이터 공급사 (DXTnavis) 협업** + upstream PR" |

---

## 5. 결과

### 5.1 산출물

- `docs/analysis/lg-ax-job-fit.md` — 11 섹션, 약 410줄
- `docs/tasklog/lg-ax-job-fit-doc-20260414.md` — 이 파일
- `docs/PROJECT-JOURNAL.md` — Timeline + Where-to-find table 1줄씩 추가

### 5.2 JD 매칭 정량 결과

| 카테고리 | 매칭 결과 |
|----------|-----------|
| 필수 (4 항목) | **4/4 ✅** (학력 / Python / ML·DL 기본 / 문제해결) |
| 업무 (8 항목) | **8/8 매칭** (그 중 6 ✅ + 2 🟡 honest gap = MLOps 직접 학습 / DL 모델 학습) |
| 우대 (5 항목) | **3 ✅ + 1 🟡 + 1 ❌** (TF/PyTorch 만 명백 부재) |

### 5.3 다음 단계 (Path B → Path A 안전 진행)

1. ✅ doc 작성 완료 (이 task)
2. ⏸ 사용자 검토 — 톤·내용·LG 컨텍스트 적합성 확인
3. ⏸ 검토 결과 반영 후 **Notion portfolio 페이지에 단독 섹션 추가**
   (Refinery Facility Ontology Analytics 페이지 본문)
4. ⏸ R11 marker 가 자동 렌더되는지 확인 (이력서 view / portfolio view)

### 5.4 보완 액션 후보 (사용자 결정 대기)

- **Task A (PyTorch MLP) 구현** — deep-dive §8 의 미분류 객체 자동 분류
  → portfolio 의 "DL 학습 경험" 항목 채움 (~1주)
- **EXAONE 어댑터 PoC** — `src/bimkg/llm/agent.py` 에 EXAONE 어댑터
  옵션 추가 (LG AI Research 환경 시뮬레이션)
- **Foundry Workshop 앱** — 6 ObjectType 위에 자연어 질의 UI (이미 backend
  완료, frontend 만 추가)

---

## 참조

- 신규 doc: [`docs/analysis/lg-ax-job-fit.md`](../analysis/lg-ax-job-fit.md)
- 미러 패턴: [`docs/analysis/ontology-kg-engineer-perspective.md`](../analysis/ontology-kg-engineer-perspective.md)
- 입력 자료: [`docs/analysis/data-analyst-data-scientist-deep-dive.md`](../analysis/data-analyst-data-scientist-deep-dive.md)
- R11 룰: [dev-standards@0.4.0](https://github.com/tygwan/dev-standards) (R11 v0.2.0)
- Notion: <https://www.notion.so/Refinery-Facility-Ontology-Analytics-3405a4e1f87881d08fd4f9ed41234793>
