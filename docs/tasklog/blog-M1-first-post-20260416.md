# M1 수사극 기술블로그 첫 번째 글 + Notion 갤러리 DB 연동

**일자**: 2026-04-16
**담당 Task**: #7~#10 (navi + 블로그 + Notion + 문서화)
**커밋**: (pending)

---

## 1. 언어 / 내용

dev-standards R11 의 "기록된 finding 을 기술블로그 narrative 로 풀어쓰는 패턴"
을 처음으로 실험. M1 Piping 오분류 finding 을 개인 블로그 장문으로 풀어쓰고,
Notion 의 갤러리 DB 로 포스트 관리 체계 구축.

| # | 산출물 | 입력 | 출력 |
|:-:|--------|------|------|
| 1 | PROJECT-JOURNAL §0 "독자별 Entry Point" 섹션 | 페르소나 6개 | 5줄 탐색 표 (진입 시간 포함) |
| 2 | `docs/blog/2026-04-M1-piping-misclassification.md` | Finding M1 archive 전체 | 345줄 / ~4,800자 / 읽기 12분 (존댓말, 저자 소개 포함) |
| 3 | Notion M1 포스트 페이지 | 위 markdown + `01_piping_confidence.png` | ~80 blocks (heading/paragraph/table/code/bullet/divider) + 커버 + 🔍 아이콘 |
| 4 | `docs/blog/blog-writing-retrospective.md` | M1 글쓰기 경험 | 11 narrative 패턴 + R12 룰 초안 + 다음 글 후보 |
| 5 | 이 task log | — | 5-section R2 기록 |

### 1.1 신규/수정 파일

```
docs/blog/                                          # NEW directory
├── 2026-04-M1-piping-misclassification.md          # NEW (345 lines)
└── blog-writing-retrospective.md                   # NEW (R12 룰 후보)

docs/tasklog/
└── blog-M1-first-post-20260416.md                  # NEW (이 파일)

docs/PROJECT-JOURNAL.md                              # MODIFIED
                                                     # ├── §0 독자별 Entry Point 추가
                                                     # ├── Timeline M1 블로그 entry 추가
                                                     # └── Where-to-find 블로그 링크
```

Notion 반영:
- 기술 블로그 페이지 (`3435a4e1...5b975`) 에 M1 포스트 배치
- 사용자가 inline database (`3435a4e1...6701d`) 수동 생성 → M1 이 DB 첫 row 로 이동
- M1 의 `태그` 프로퍼티 6개 값 입력 (regex · Python · data quality · word boundary · 외부 협업 · XLSX)

---

## 2. 문제

**배경**:
- 이전 세션에서 사용자 피드백: "기술블로그처럼 디테일하게 글을 써내려 가는 것이 원했던 형태. 블로그 글에서 이력서·요약 추출이 쉬워짐"
- dev-standards 현재 커버리지 (R1~R11) 는 **기록·추출** 중심. **장문 narrative** 작성 룰 부재
- 옵션 C 선택: 실제 블로그 1편 작성 후 패턴을 귀납해 R12 설계

**구체 요구**:
1. M1 수사극을 기술블로그 형식으로 작성 (토스플레이스 <https://toss.tech/article/place-metric-review> 스타일 참조)
2. Notion 갤러리뷰로 포스트 관리
3. 문체: 존댓말 + 저자 소개 + 시행착오 유지 + CTA 제외 (Notion 공간)
4. 커버: M1 confidence figure 재사용

**추가 발견 (세션 중)**:
- Notion MCP 의 `create-a-data-source` / `retrieve-a-data-source` / `update-a-data-source` 모두 `invalid_request_url` 반환
- 갤러리 DB 자동 생성 불가 → 사용자 수동 생성 + 제가 row push 전략 필요

---

## 3. 분석

### 3.1 문체·구조 결정

토스플레이스 글 분석 (문체 분석 via WebFetch) 결과:
- 존댓말 "저희가 ~해요" (조직 톤) vs 개인 에세이 "나는 ~했다" (1인칭)
- 저자 소개 hook vs 수치 hook
- 성공 서사 vs 시행착오 노출

**선택**: 토스의 존댓말 + 저자 소개 차용 + M1 의 시행착오 구조 유지 ((a)+(b) 조합).

### 3.2 Notion DB 전략

MCP 스키마 한계 발견 후 3가지 경로 검토:
- A: 현재 페이지를 DB 로 승격 — 사용자가 UI 에서 inline database 생성
- B: DB 를 별도 생성 후 M1 재 push
- **C: A 의 하위 집합 — M1 을 child page 로 먼저 push, 사용자가 DB 생성, 이후 속성 patch** ✅ 채택

사용자가 DB 생성 + M1 이동까지 자동 처리 (Notion UI 의 child_page → DB row 전환 지원).

### 3.3 패턴 추출 방식

글 작성하며 **메타 메모 없이** 씀 → 완성 후 회고 문서로 패턴 재구성.
이 방식은 "글쓰기 몰입" 을 깨지 않음. R11 의 재료-작업 분리 원칙 동일.

---

## 4. 해결

### 4.1 작업 순서 (실제 실행)

1. TaskCreate 4개 (#7 navi, #8 draft, #9 Notion push, #10 문서화)
2. PROJECT-JOURNAL §0 에 독자별 Entry Point 표 추가 (6 페르소나)
3. M1 블로그 초안 작성 — 9 섹션, 평서체 "~다" 초안
4. 토스 참조 글 WebFetch 로 분석 → 리팩토링
5. 전면 존댓말 전환 + 저자 소개 2 단락 + 독자 기대 설정
6. Notion 페이지 생성 (cover + icon + initial blocks)
7. 4 배치로 본문 append (~80 blocks total, tables/code/bullets/numbered 정상)
8. DB 자동 생성 실패 → 사용자에게 UI 수동 생성 안내
9. 사용자가 DB 생성 완료 → M1 페이지가 DB row 로 자동 전환
10. `태그` 프로퍼티 6개 값 입력
11. 본 회고 문서 + task log 작성
12. Git 커밋

### 4.2 MCP 제약 해결 전략

```
create-a-data-source    → FAIL → 사용자 UI 수동 생성
retrieve-a-data-source  → FAIL → retrieve-a-database 로 대체 (2022-06-28 엔드포인트)
update-a-data-source    → FAIL → 사용자가 UI 에서 프로퍼티 추가 요청
patch-block-children    → OK   → 본문 push 전부 이것으로
post-page               → OK   → 초기 페이지 + 커버 + 아이콘 + first blocks
patch-page              → OK   → 태그 등 프로퍼티 값 입력
retrieve-a-database     → OK   → DB schema 확인
retrieve-a-page         → OK   → DB row 상태 확인
get-block-children      → OK   → 페이지 구조 확인
```

### 4.3 프로퍼티 완성도 계획

- 사용자가 추가 프로퍼티 6개 (발행일 · 상태 · 카테고리 · Finding 연결 · 요약 · 읽기 시간) Notion UI 수동 추가 요청 중
- 추가 완료 시 제가 `API-patch-page` 로 M1 값 한 번에 입력
- **현재 완료된 값**: 태그 (6개 multi-select)
- **대기 중인 값**: 나머지 6개 프로퍼티

---

## 5. 결과

### 5.1 정량 산출물

| 지표 | 값 |
|------|-----|
| 블로그 글 길이 | 345 lines / 10,429자 (한글 ~4,800자) |
| 섹션 수 | 9개 본문 섹션 + 저자 소개 + 참조 + meta |
| Notion 블록 수 | ~80 (heading 8, paragraph 30+, table 7, code 5, bulleted 15+, numbered 11, divider 2) |
| Notion 배치 횟수 | 5 (page 생성 1 + append 4) |
| Narrative 패턴 추출 | 11개 (P1~P11) |
| R12 룰 초안 | 6개 섹션 (Input/Sections/Elements/Metadata/Length/Variants) |
| 다음 블로그 후보 | 3개 (M3 scope-drift / R10 arc / 7-Phase 장문) |

### 5.2 정성 결과

**성공**:
- 토스 스타일 흡수 + 개인 에세이 깊이 유지 → 공존 가능성 확인
- Finding archive 만으로 4,800자 글 완성 → R3 이 블로그 창고 역할 확정
- Notion 본문 렌더링 (tables, code, links) 모두 정상 → 개인 블로그로도 충분히 presentable

**제약 확인**:
- Notion 2025-09-03 data_source API 는 현 MCP 에서 사용 불가
- DB schema 조작은 사용자 UI 의존
- 커버 이미지는 public repo raw URL 의존 (Notion files API 미지원)

### 5.3 다음 단계

1. **사용자 프로퍼티 추가 대기** → 완료 시 M1 값 6개 patch
2. **다음 블로그** — 추천: M3 parent box (variant 검증)
3. **3편 누적 후 R12 룰 초안 확정** → dev-standards 에 upstream
4. **블로그 작성 skill 후보** — 반복 작업이면 plugin/skill 로 자동화 고려

---

## 참조

- 블로그 글: [`docs/blog/2026-04-M1-piping-misclassification.md`](../blog/2026-04-M1-piping-misclassification.md)
- 작성 회고: [`docs/blog/blog-writing-retrospective.md`](../blog/blog-writing-retrospective.md)
- 원본 finding: [`docs/findings/2026-04-12-M1-piping-misclassification/`](../findings/2026-04-12-M1-piping-misclassification/)
- Notion 포스트: <https://www.notion.so/Piping-997-Structure-3435a4e1f87881f5b052cd7cd3d96407>
- 토스 참조: <https://toss.tech/article/place-metric-review>
- dev-standards: <https://github.com/tygwan/dev-standards>
