# Documentation Index

이 디렉터리는 Ontology for CM 프로젝트의 모든 문서를 담고 있습니다.
문서는 역할별로 분류됩니다.

> **🗂 프로젝트 전체 스토리를 한 번에 보고 싶다면**:
> [`PROJECT-JOURNAL.md`](PROJECT-JOURNAL.md) — 문제, 결정, 타임라인을 한 문서에서 내비게이션.

## 언제 무엇을 읽어야 하나

| 상황 | 읽을 문서 |
|------|----------|
| **"어떤 문제를 마주했었지?"** | [`PROJECT-JOURNAL.md`](PROJECT-JOURNAL.md) ← 단일 포털 |
| 프로젝트를 처음 접할 때 | [../README.md](../README.md) + [plan/pipeline-implementation-plan.md](plan/pipeline-implementation-plan.md) |
| 발견된 데이터 이슈 상세 | [findings/](findings/) |
| Phase 별 작업 기록 | [tasklog/](tasklog/) |
| 설계 결정 근거 | [analysis/](analysis/) |
| 원본 데이터 구조 | [reference/DATA-SPECIFICATION.md](reference/DATA-SPECIFICATION.md) |
| XLSX 분류기 로직 상세 | [analysis/refined-xlsx-exporter-logic.md](analysis/refined-xlsx-exporter-logic.md) |
| 옛 C# 백엔드 분석 자료 | [reference/dxtnavis-2026-04-07-*.md](reference/) |

## 디렉터리 구조

```
docs/
├── PROJECT-JOURNAL.md            단일 포털: 문제/결정/타임라인
├── README.md                         (이 문서)
│
├── plan/                             계획 문서 — "앞으로 무엇을 할 것인가"
│   └── pipeline-implementation-plan.md
│
├── analysis/                         설계 결정 — "왜 이렇게 정했는가"
│   ├── phase-1a-data-realignment-design.md
│   └── refined-xlsx-exporter-logic.md
│
├── tasklog/                          작업 기록 — "무엇을 했는가"
│   ├── README.md
│   └── phase-*.md
│
├── findings/                         데이터 이슈 아카이브 — "무슨 문제에 부딫혔는가"
│   ├── README.md                     (findings index)
│   ├── TEMPLATE.md                   (new finding template)
│   └── YYYY-MM-DD-ID-slug/           (per-issue folder with audit.py, data/, figures/)
│
└── reference/                        외부 참조 — "사전 자료는 무엇이 있었는가"
    ├── DATA-SPECIFICATION.md
    └── dxtnavis-2026-04-07-*.md
```

## 문서 유형별 역할

### plan/
**"무엇을 할 것인가"** — 미래 지향적 계획 문서.
각 Phase 의 목표, 의존 관계, 산출물, 검증 기준을 정의한다.

### analysis/
**"왜 이렇게 정했는가"** — 설계 결정의 근거.
여러 option 의 trade-off, 선택 이유, 숨은 전제, 메타 원칙을 기록한다.
코드 리뷰 시 "이 선택이 타당했는지" 검증하는 기준점.

### tasklog/
**"무엇을 했는가"** — 완료된 작업의 소급 기록.
5개 섹션 고정 포맷 (언어/내용, 문제, 분석, 해결방안, 결과).
각 Phase 또는 중요 작업 완료 시마다 작성.

### reference/
**"사전 자료"** — 외부 소스의 참조 문서.
DXTnavis 프로젝트의 DATA-SPECIFICATION, baseline insights 등.
이 프로젝트에서 새로 작성한 것이 아니라 참고용으로 보관.

## 문서 작성 규칙

1. **언어**: 한국어 기본, 기술 용어 및 코드 인용은 영어
2. **파일명**: `kebab-case.md`, Phase 별 문서는 `phase-N-identifier.md`
3. **크로스 레퍼런스**: 상대 경로 사용 (`[text](../other/doc.md)`)
4. **코드 블록**: 언어 명시 (` ```python `, ` ```bash `, ` ```sql `)
5. **테이블**: Markdown 파이프 스타일 일관 유지
