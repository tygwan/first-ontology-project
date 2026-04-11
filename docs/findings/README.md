# Findings Archive

> 데이터 이슈 및 품질 문제가 발견될 때마다 이 디렉터리에 **보관 / 정리 / 시각화 / 기록 / 커밋** 합니다.
>
> 목적: 프로젝트 진행 중 어떤 문제에 부딫혔고, 어떻게 분석하고 해결했는지의
> **기술적 의사결정 일지** 로 사용합니다. 감사, 회고, 이해관계자 설명 시 근거 자료.

---

## 기록 규칙 (요약)

각 이슈는 아래 구조로 저장됩니다:

```
docs/findings/YYYY-MM-DD-<severity>-<slug>/
├── README.md        # 5 섹션: Finding, Evidence, Analysis, Resolution, References
├── audit.py         # 재현 가능한 진단 스크립트
├── data/            # CSV 증거 파일 (집계/샘플)
└── figures/         # matplotlib 시각화 (최소 1개)
```

상세 규칙: `memory/feedback_finding_archive.md` 참조.

## Index

| Date | ID | Severity | Title | Status |
|------|----|:-:|-------|--------|
| 2026-04-12 | M1 | 🟠 MAJOR | [Piping misclassification via XLSX substring matching](2026-04-12-M1-piping-misclassification/README.md) | 🔄 Open |

### Severity 정의

- 🔴 **CRITICAL**: downstream phase 가 실행 불가 또는 완전 잘못된 결과 생성
- 🟠 **MAJOR**: downstream 결과가 부분적으로 틀리지만 기능은 유지. 수정 권장
- 🟡 **MINOR**: 표시/UX 문제, 희귀 엣지 케이스, 알려진 한계

### Status 정의

- 🔄 **Open**: 조사 중 또는 결정 대기
- 🛠 **Fixing**: 해결 진행 중
- ✅ **Resolved**: 해결 완료 (resolution_commit, 테스트 포함)
- 📋 **Deferred**: 의도적으로 후속 Phase 로 연기
- 🔭 **Accepted**: 원천 한계로 수용
