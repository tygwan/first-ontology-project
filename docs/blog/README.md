# 기술 블로그 인덱스

> 프로젝트에서 발견한 기술적 경험을 narrative 장문으로 풀어쓴 글 모음.
> 이력서의 "더 자세히" 링크 타겟이자, Notion 갤러리 DB 와 동기화됩니다.
>
> Notion 갤러리: <https://www.notion.so/3435a4e1f878804fb906eb605b53b975>

---

## 프로젝트별 글 목록

### 🏭 Refinery Facility Ontology Analytics

| # | 제목 | 카테고리 | Finding | 읽기 시간 |
|:-:|------|---------|---------|:---------:|
| 1 | [Piping 으로 분류된 997 객체가 사실은 Structure 였던 이유](refinery/2026-04-M1-piping-misclassification.md) | 수사극 | M1 | 12분 |
| — | (예정) Parent Box 448개가 그래프를 66% 오염시키고 있었다 | 수사극 | M3 | ~10분 |
| — | (예정) Louvain vs Grid: modularity 0.18 → 0.42 의 이야기 | 회고 | — | ~8분 |

### 🎯 기본기 검증 (Fundamentals)

| # | 제목 | 언어/기술 | 읽기 시간 |
|:-:|------|----------|:---------:|
| — | (예정) `\b` 는 "단어" 가 아니라 "문자 전환" | Python · Regex | ~5분 |

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
└── fundamentals/                   # 기본기 자가점검 글 (언어별 하위)
    ├── python/
    ├── regex/
    ├── sql/
    └── git/
```
