# 기술 블로그 인덱스

> 프로젝트에서 발견한 기술적 경험을 narrative 장문으로 풀어쓴 글 모음.
> 이력서의 "더 자세히" 링크 타겟이자, Notion 갤러리 DB 와 동기화됩니다.
>
> Notion 갤러리: <https://www.notion.so/3435a4e1f878804fb906eb605b53b975>

---

## 프로젝트별 글 목록

### 🏭 Refinery Facility Ontology Analytics
*2025.07 ~ 진행중 · BIM 12,009 객체 → OWL 온톨로지 + LangGraph 에이전트*

| # | 제목 | 카테고리 | Finding | 읽기 시간 |
|:-:|------|---------|---------|:---------:|
| 1 | [Piping 으로 분류된 997 객체가 사실은 Structure 였던 이유](refinery/2026-04-M1-piping-misclassification.md) | 수사극 | M1 | 12분 |
| — | (예정) Parent Box 448개가 그래프를 66% 오염시키고 있었다 | 수사극 | M3 | ~10분 |
| — | (예정) Louvain vs Grid: modularity 0.18 → 0.42 의 이야기 | 회고 | — | ~8분 |

### 🔧 DXTNavis
*2025.09 ~ 진행중 · Navisworks C# 플러그인, BIM 데이터 추출 + 4D 시뮬레이션*

| # | 제목 | 카테고리 | 읽기 시간 |
|:-:|------|---------|:---------:|
| — | (예정) 445K 프로퍼티 추출을 5분으로 — Navisworks COM API 래핑 회고 | 회고 | ~10분 |
| — | (예정) PR #3 의 첫 fix 가 왜 실패했나 — `\b` 의 함정 (Refinery 와 연결) | 수사극 | ~8분 |

### 👁 VLM-based Labeling Automation
*2024.02 ~ 2026.02 · Florence-2 + SAM2 + ResNet, F1 52→88%*

| # | 제목 | 카테고리 | 읽기 시간 |
|:-:|------|---------|:---------:|
| — | (예정) F1 52% → 88% — VLM 도메인 한계를 ResNet few-shot 으로 보완하기 | 설계 | ~12분 |
| — | (예정) autodistill 포크해서 5개 모듈 추가한 이야기 | 회고 | ~8분 |

### 📊 보행자 안전 위험요소 프로파일링
*2023.05 ~ 2023.11 · 1저자 설문 연구, 12,600 응답*

| # | 제목 | 카테고리 | 읽기 시간 |
|:-:|------|---------|:---------:|
| — | (예정) "보행로 자체"가 최대 위험요소 — 분류 기준에서 빠진 항목의 역발견 | 회고 | ~10분 |
| — | (예정) PySimpleGUI 로 12,600 응답 데이터셋 직접 만든 회고 | 튜토리얼 | ~8분 |

### 🎯 기본기 검증 (Fundamentals)

| # | 제목 | 언어/기술 | 읽기 시간 |
|:-:|------|----------|:---------:|
| — | (예정) `\b` 는 "단어" 가 아니라 "문자 전환" — Pipe Rack 사례 | Python · Regex | ~5분 |

---

## 메타 문서

- [블로그 작성 회고 — M1 에서 발견한 11 narrative 패턴](blog-writing-retrospective.md)
  - R12 (Narrative Writing Rule) 룰 초안 포함

---

## 디렉토리 구조

```
docs/blog/
├── README.md                       # 이 파일
├── blog-writing-retrospective.md   # 메타 (프로젝트 무관)
├── refinery/                       # Refinery 프로젝트 글
│   └── 2026-04-M1-piping-misclassification.md
├── dxtnavis/                       # DXTNavis 프로젝트 글 (예정)
├── vlm/                            # VLM 컴퓨터비전 프로젝트 글 (예정)
├── survey/                         # 설문연구 프로젝트 글 (예정)
└── fundamentals/                   # 기본기 자가점검 글 (언어별 하위)
    ├── python/
    ├── regex/
    ├── sql/
    └── git/
```

---

## 글 작성 우선순위 (R12 룰 검증 순서)

1. ✅ M1 수사극 (refinery) — 2-attempt detective variant
2. ⏭ M3 parent box (refinery) — scope-drift variant
3. ⏭ Louvain vs Grid (refinery) — single-attempt + 룰 정립 variant
4. ⏭ 첫 기본기 글 — `\b` 의 함정 (M1 에서 파생, fundamentals/regex/)

3편 누적 후 dev-standards 의 R12 (Narrative Writing) 룰 초안을 확정하고 upstream.
