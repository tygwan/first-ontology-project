# 블로그 작성 회고 — M1 수사극을 풀어쓰며 발견한 패턴

> 이 문서는 `2026-04-M1-piping-misclassification.md` 블로그 글을 작성하면서
> 발견한 narrative 패턴을 정리한 회고입니다. 2~3 편을 더 작성한 뒤 공통
> 패턴을 추출해 dev-standards 의 **R12 (Narrative Writing) 룰** 로
> 승격시킬 것을 전제로 합니다.
>
> **작성일**: 2026-04-16
> **대상 글**: [`2026-04-M1-piping-misclassification.md`](2026-04-M1-piping-misclassification.md) (345 lines, ~4,800자, 읽기 12분)
> **Notion 반영**: <https://www.notion.so/Piping-997-Structure-3435a4e1f87881f5b052cd7cd3d96407>

---

## 1. 이 글쓰기가 검증한 가설

**가설**: 프로젝트 포털(`PROJECT-JOURNAL`) + Finding archive(R3) + Task log(R2) 의
기록만 있으면 기술블로그 장문을 **무에서 짓지 않고** 풀어쓸 수 있다.

**결과**: ✅ 확인. M1 글을 쓰면서 **새로 계산하거나 조사한 것은 0건** 이었습니다.
모든 수치·코드·표는 `docs/findings/2026-04-12-M1-piping-misclassification/` 에
이미 존재했고, 글쓰기는 그 재료를 **시간순 서사** 로 배치하는 작업이었습니다.

의미: R3 (Finding Archive Rule) 은 "감사 재현성" 을 위한 룰이었지만
**블로그 재료 창고의 역할도 겸함**. 두 번째 이득.

---

## 2. 발견한 Narrative 패턴 11개

### 2.1 입력 구조 (글쓰기 전 재료)

**P1. Material proximity** — Finding archive 하나가 블로그 한 편의 입력 전체
- `README.md` = 구조적 스켈레톤 (문제·분석·해결·근거)
- `audit.py` = 재현 가능성 증명
- `figures/*.png` = 시각 자산 (블로그 커버 포함)
- `data/*.csv` = 원시 증거
- **블로그 작성자는 "무엇을 쓸지" 를 정하는 것이 아니라 "어떻게 배치할지" 만 고민**

**P2. Timeline as arc** — 실제 사건 흐름이 그대로 narrative arc 가 됨
- 발견 → 1차 추적 → 근원 찾기 → 옵션 정리 → 첫 시도 → 실패 → 재설계 → 드리프트 발견 → 회고
- **인위적 arc 를 만들 필요 없음** — Finding archive 의 §2~§4 가 자연스럽게 장 구분이 됨

### 2.2 오프닝 구조

**P3. 저자 소개 2단락** — 토스 스타일 차용
- 첫 단락: "누구인가 · 어떤 프로젝트" (1~2문장)
- 둘째 단락: "이 글이 다룰 내용 예고" (+ 독자가 가져갈 것)
- 길이 제약: 합쳐서 150~200자 이내

**P4. 수치 hook** — 첫 섹션은 "이상한 현상" 의 구체 수치로 시작
- "997개가 24.8%" 는 "오분류가 많다" 보다 10배 강력
- **추상어 대신 측정값** 으로 여는 것이 장기 독자 기억에 남음

### 2.3 본문 전개

**P5. Frontmatter replacement** — DB 프로퍼티 없을 때 상단 inline 메타
- Notion 갤러리 DB 가 없는 페이지에서도 동일 정보 전달 가능
- 형식: `📅 발행일 · 🔴 Finding · 🖋 상태 · ⏱ 읽기 시간` 한 줄 + 태그 한 줄
- **독자 기대 설정**: "이 글이 얼마 걸리는지, 어떤 카테고리인지" 즉시 파악

**P6. Code block as evidence** — 주장의 증명은 실제 코드 인용
- "substring 매칭이 문제다" 는 텍스트로 쓰지 않고 C# 원본 9줄을 그대로 붙임
- 독자는 verify 가능 → 신뢰도 상승

**P7. Table for fact compression** — 여러 케이스를 한눈에
- M1 글은 7개의 표 사용 (객체 샘플 · 원인 집계 · 4 옵션 · 매치 결과 · Before/After · snapshot drift 등)
- 각 표는 3~7행 규모. 더 크면 지루, 더 작으면 산문이 나음

**P8. 솔직한 실패 섹션 (Emotional peak)** — "첫 fix 의 실패 — `\b` 의 함정"
- 이 섹션이 글 전체의 **감정 고점**
- 엔지니어가 공감하는 순간이 여기 — "나도 `\b` 가 작동할 줄 알았지"
- **성공 서사만 쓰면 얕아짐**. 실패와 교정 과정이 기술글의 깊이를 만든다

### 2.4 마무리 구조

**P9. 회고 → 룰 승격** — 이 경험이 룰이 된 이유
- 개인 경험 → 팀 표준 전환을 명시적으로 서술
- "R3 Finding Archive Rule" 같이 **이름 붙은 산출물** 로 연결

**P10. 엔지니어가 가져갈 것 (Numbered takeaways)** — 6개 교훈
- 각 항목: `### N. 한 줄 주장` + 1문단 설명
- **일반화 수준 주의**: "substring 매칭 조심" 은 유용, "조심하세요" 는 공허
- 독자가 자기 코드에 바로 적용 가능한 수준이 정답

**P11. Meta footnote** — 글의 자기 참조
- "이 글은 dev-standards R11 실험 중..." 이탤릭 1 문장
- 글이 제품 (dev-standards 룰) 을 뒷받침하는 실험임을 명시

---

## 3. 이번에 특수했던 것 (일반화 주의)

M1 에만 해당되고 다른 글로 일반화하기 힘든 요소:

- **`\b` 의 함정** 같은 구체 기술 depth — M3, R10 블로그는 완전히 다른 기술 층위
- **6 takeaways** 는 M1 의 우연. M3 는 3, R10 은 8 이 적절할 수 있음
- **"첫 fix → 실패 → 진짜 fix" 2-attempt arc** — M2 는 single-attempt, M3 는 drift 발견형
- **외부 PR 기여** 는 M1·M3 에만 있음. 내부 finding 만으로 끝나는 글도 존재

**R12 설계 시사점**: narrative 템플릿은 **단일 arc 강제가 아닌 variant set** 으로
설계해야 함. 최소 3개 variant 필요:
1. 2-attempt detective (M1 형)
2. Single-attempt diagnosis (M2 형)
3. Scope-drift discovery (M3 형)

---

## 4. Notion 반영 과정의 교훈

### 4.1 MCP API 제약 노트

- `API-create-a-data-source` / `API-retrieve-a-data-source` / `API-update-a-data-source` — **모두 `invalid_request_url` 반환 (2026-04-16)**. Notion 2025-09-03 data_source 엔드포인트 routing 실패로 추정
- `API-patch-block-children` / `API-post-page` / `API-patch-page` / `API-retrieve-a-database` — 정상
- **워크어라운드**: DB 는 사용자가 UI 에서 수동 생성, 제가 row 로 push + 속성값 patch

### 4.2 블록 타입 실제 지원 범위

MCP 스키마는 `paragraph` · `bulleted_list_item` 만 명시하지만 실제로는 더 많이 허용:
- ✅ `heading_1`, `heading_2`, `heading_3`
- ✅ `numbered_list_item`
- ✅ `code` (language 지정 가능: python, c#, etc.)
- ✅ `table` (with `table_row` children, `table_width`, `has_column_header`)
- ✅ `divider`
- ✅ rich_text annotations: `bold`, `italic`, `code`, `color`
- ✅ rich_text with `link` (URL)

**실전 팁**: 스키마의 `anyOf` 제약은 일단 무시하고 표준 Notion block 타입을 그대로 전달.

### 4.3 배치 크기

- 1 batch 당 ~30 blocks 가 안정
- 큰 table (`table_row` children 포함) 이 있으면 block 카운트가 누적됨
- M1 전체는 5 batches 로 분할 (page 생성 1 + append 4)

### 4.4 커버 이미지

- GitHub raw URL 사용 (public repo 전제): `https://raw.githubusercontent.com/<user>/<repo>/main/<path>`
- Finding archive 의 figure 를 그대로 재활용 → **별도 디자인 작업 0**
- 로컬 파일 업로드 방식 필요 시 Notion files API 가 필요하지만 MCP 미지원

---

## 5. R12 (Narrative Writing Rule) 후보 초안

3편 이상의 블로그가 쌓이면 아래 구조로 dev-standards 에 승격 후보.

```
# R12 — Narrative Writing Rule

## 5.1 Input
- R3 Finding archive 1개 (또는 Task log 묶음)
- 최소 산출물: audit 스크립트 + 1개 이상 figure + 결정 trace

## 5.2 Required sections
- 저자 소개 (2 단락, 150~200자)
- 수치 hook 으로 시작하는 도입
- Timeline 을 그대로 따르는 본문 (arc variant 중 선택)
- 회고 섹션 (룰 승격 명시)
- 교훈 섹션 (3~8개 numbered takeaways)
- Meta footnote (self-reference)

## 5.3 Required elements
- 최소 1개 code block (증거)
- 최소 1개 table (사실 압축)
- 최소 1개 시행착오 / 실패 섹션 (Emotional peak)

## 5.4 Required metadata (frontmatter 또는 DB property)
- 발행일 · 카테고리 · 태그 · Finding 연결 · 상태 · 읽기 시간 · 요약

## 5.5 Length target
- 본문 4,000~5,000자 (한국어 기준)
- 읽기 10~12분

## 5.6 Narrative arc variants
- V1: 2-attempt detective
- V2: Single-attempt diagnosis
- V3: Scope-drift discovery
- (향후 추가)
```

---

## 6. 다음 블로그 후보 (패턴 검증용)

### 후보 A — "Parent Box 448개가 그래프를 66% 오염시키고 있었다" (M3)
- variant: scope-drift 형 (AABB precision → parent/child 계층 → 구조적 발견)
- 재료: `docs/findings/2026-04-13-M3-parent-box-contamination/`
- 예상 분량: ~4,000자

### 후보 B — "Louvain vs Grid: modularity 0.18 → 0.42 의 이야기" (R10 탄생기)
- variant: single-attempt + 룰 정립형
- 재료: `docs/PROJECT-JOURNAL §4 D?` + 시공 존 분석
- 예상 분량: ~3,000자

### 후보 C — "정유시설 BIM 12K 에서 LLM Agent 까지 — 7 Phase 회고" (장문)
- variant: 전체 여정 회고
- 재료: `PROJECT-JOURNAL §2 Timeline` 전체
- 예상 분량: ~12,000자 (장문)

**추천 순서**: A → B → C. A 는 M1 과 다른 variant 검증, B 는 arc 의 간결성
검증, C 는 장문 감당 가능성 검증.

---

## 7. 참조

- 본 회고의 대상 블로그: [`2026-04-M1-piping-misclassification.md`](2026-04-M1-piping-misclassification.md)
- Notion 반영: <https://www.notion.so/Piping-997-Structure-3435a4e1f87881f5b052cd7cd3d96407>
- 원본 finding: [`docs/findings/2026-04-12-M1-piping-misclassification/`](../findings/2026-04-12-M1-piping-misclassification/)
- 토스 참조 글: <https://toss.tech/article/place-metric-review> (문체 · 저자 소개 · 구조 레퍼런스)
- dev-standards (R11 현재 / R12 후보): <https://github.com/tygwan/dev-standards>

---

*이 회고 자체가 "회고 → 룰 후보" 패턴 (P9) 의 메타 적용례입니다.*
