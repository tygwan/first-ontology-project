# AI FDE Session Log

**목적**: AI FDE (Foundry Forward Deployed Engineer AI application) 와의 협업 세션을 **의사결정 중심**으로 기록.

각 세션은 단순 대화 기록이 아니라 **"어떤 질문이 제기되었고, 무엇을 결정했으며, 왜 그렇게 결정했는가"** 를 남기는 Decision Record 입니다.

---

## 왜 기록하는가

1. **재현성**: 6개월 후 내가 왜 이 Ontology 구조를 골랐는지 알 수 있어야 함
2. **협업**: 팀원이 합류할 때 과거 의사결정 맥락 공유
3. **포트폴리오**: AI-augmented engineering workflow 의 증빙 자료
4. **학습**: AI FDE 가 놓친 것 / 잘 지적한 것을 리뷰해서 프롬프트 기술 향상

---

## 구조

```
docs/analysis/ai-fde-sessions/
├── README.md                              ← 이 파일
├── _template.md                           ← 새 세션 시작 시 복사해서 쓰는 템플릿
├── 2026-04-15-phase1-exploration.md       ← Phase 1 탐색 세션
├── 2026-04-15-phase2-ontology-modeling.md ← Phase 2 (예정)
└── 2026-04-15-phase3-advancement.md       ← Phase 3 (예정)
```

---

## Session 목록

| Date | Phase | Topic | Key Decisions | Status |
|---|---|---|---|---|
| 2026-04-15 | 1 | Data Exploration | 5 design questions answered (Ontology structure, Pipeline first-class, filter strategy, adjacency tier, app priority) | ✅ Complete |

---

## 세션 기록 원칙

### DO ✅
- **AI FDE 질문은 그대로** 인용 (paraphrase 금지)
- **각 결정에 Rationale 섹션** 필수
- **대안(alternatives considered)** 기록
- **관련 문서 cross-reference**
- **다음 세션 action items** 마무리

### DON'T ❌
- 대화 전체를 verbatim 복사 (길어지고 의사결정이 묻힘)
- "AI FDE가 말함" 식의 피상적 기록
- 결정 없이 탐색만 기록
- 포트폴리오용 미화 (있는 그대로)

---

## 관련 문서

- **세션 스크립트**: `docs/plan/ai-fde-session-scripts/` — 세션 진행 시 사용한 프롬프트 원본
- **Dataset Profiles**: `docs/analysis/foundry-dataset-profiles-2026-04-15.md` — 세션 context
- **PROJECT-JOURNAL**: `docs/PROJECT-JOURNAL.md` §4 — 최상위 Decision Record 와 연결
- **Findings**: `docs/findings/` — 세션 중 발견한 새 이슈는 여기로
