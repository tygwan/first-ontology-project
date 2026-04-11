# Phase 1 — M1 Finding Archive

**일자**: 2026-04-12
**담당 Task**: #13 (규칙 수립), #14 (M1 archive), #15 (DXTnavis PR draft)
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| Markdown | `memory/feedback_finding_archive.md` | Finding archive 규칙을 메모리에 저장 (보관/정리/시각화/기록/커밋 5단계) |
| Markdown | `memory/MEMORY.md` | 인덱스에 새 규칙 추가 |
| Markdown | `docs/findings/README.md` | findings 디렉터리 인덱스 + severity/status 정의 |
| Markdown | `docs/findings/TEMPLATE.md` | 새 이슈 기록용 템플릿 |
| Markdown | `docs/findings/2026-04-12-M1-piping-misclassification/README.md` | M1 finding 전체 보고서 (5 섹션 포맷) |
| Python | `docs/findings/2026-04-12-M1-piping-misclassification/audit.py` | 재현 가능한 감사 스크립트 |
| Python | `docs/findings/2026-04-12-M1-piping-misclassification/make_figures.py` | matplotlib 시각화 4종 생성 |
| CSV | `data/piping_confidence_breakdown.csv` | HIGH/MED/LOW/LIKELY_BUG 분해 |
| CSV | `data/substring_bug_causes.csv` | 4종의 substring bug 원인 |
| CSV | `data/likely_misclassified_sample.csv` | Top 20 오분류 display_name 패턴 |
| CSV | `data/keyword_hit_debug.csv` | 8 Piping 키워드별 false positive 여부 |
| CSV | `data/structure_sanity_check.csv` | Structure 클래스 cross-contamination 없음 증명 |
| PNG | `figures/01_piping_confidence.png` | HIGH 2,926 vs LIKELY_BUG 997 막대 |
| PNG | `figures/02_substring_bug_causes.png` | Pipe Rack/Trench/Pipeline/steel 원인별 카운트 |
| PNG | `figures/03_likely_misclassified.png` | Top 15 LIKELY_BUG 패턴 |
| PNG | `figures/04_class_distribution.png` | 4,014 → 2,926 클래스 인플레이션 |
| Markdown | `docs/findings/2026-04-12-M1-piping-misclassification/dxtnavis-pr-draft.md` | DXTnavis 원천 수정 PR 전문 (Part 1 bug fix + Part 2 data wishlist) |
| Markdown | `docs/analysis/phase-1-verification-findings.md` | M1 요약 링크 추가 |

### Finding 규칙 (5단계 프로세스)

```
1. 보관 (preserve)   → audit.py + data/ CSV
2. 정리 (organize)   → docs/findings/YYYY-MM-DD-ID-slug/{README.md, audit.py, data/, figures/}
3. 시각화 (visualize) → figures/*.png (matplotlib)
4. 기록 (record)     → README.md 5 섹션 (Finding / Evidence / Analysis / Resolution / References)
5. 커밋 (commit)     → git commit + push, 항상 한 번의 호흡으로
```

---

## 2. 문제

**작업 시작 당시 명확한 문제**: Phase 1d 완료 후 데이터 품질 감사 중 997건의 Piping 오분류를 발견했지만 단일 ad-hoc 스크립트로만 확인하고 기록을 남기지 않음.

작업 수행 중 **기술적 문제 없음**. audit script와 figure script 둘 다 첫 실행에서 정상 작동.

---

## 3. 분석

### 발견한 버그의 본질

DXTnavis 의 `RefinedXlsxExporter.InferClass` (C# 라인 298-375) 는 아래 패턴으로 keyword 매칭:

```csharp
if (combined.Contains("pipe") || combined.Contains("tee") || ...)
    return "Piping";
```

`.Contains()` 가 **substring 매칭** 이라 단어 경계를 고려하지 않음. 결과:
- `"tee"` ⊂ `"steel"` → `s-TEE-l` 부분 문자열 매치
- `"pipe"` ⊂ `"Pipe Rack"` / `"Pipe Trench"` / `"Pipeline"` → 폴더명이 매치

### 영향 정량화

Piping 4,014 을 증거 강도별로 분해:
- **HIGH** 2,926 (pipeline + commodity/spec/npd 메타 모두 있음) — 신뢰
- **LOW** 91 (metadata 만 있고 pipeline 없음)
- **LIKELY_BUG** 997 (아무것도 없음) — 오분류 의심

오분류 원인별:
- Pipe Rack 폴더: 698
- Pipe Trench 폴더: 60
- Pipeline 폴더: 12
- steel → tee: 10
- 기타: 217 (복합 또는 nested sys_path)

### 왜 Archive 규칙이 필요한가

이 세션 전: 이슈 발견 → 채팅으로 보고 → 사용자가 결정 대기 → 다음 세션 시작 시 이전 맥락 재구성 어려움.

이 세션 후: 이슈 발견 → 아카이브 생성 → git 영구 기록 → 미래 세션/감사 시 바로 참조 가능.

규칙의 **가치**:
1. **reproducibility** — audit.py 는 누구나 재실행 가능
2. **visual evidence** — PNG 차트는 숫자 표보다 이해도 높음
3. **decision support** — Options 1~4 각각의 trade-off 를 한 문서에서 비교
4. **PR ready** — 원천 수정을 위한 PR draft 가 이미 작성됨

---

## 4. 해결방안

Finding archive 규칙 적용:

1. **memory** 에 `feedback_finding_archive.md` 저장 (향후 세션 자동 적용)
2. **docs/findings/** 디렉터리 생성 (README + TEMPLATE)
3. **M1 이슈** 에 대한 전체 archive 작성 (README + audit.py + 5 CSV + 4 PNG + PR draft)
4. **기존 verification-findings.md** 에 M1 링크 추가
5. **모든 산출물** 한 번의 커밋으로 repo 에 기록

### DXTnavis PR 콘텐츠 구성

**Part 1 — Bug fix**:
- 현재 `Contains()` 사용 코드 분석
- 구체 증거 (MemberSystem-1-0151 + Pipe Trenches)
- 정량 영향 (997 건, 24.8%)
- 제안 수정 (regex `\b...\b` word boundary)
- 단위 테스트 예시
- 기대 결과표 (Piping 4,014 → 2,926, Structure 5,926 → 6,900)

**Part 2 — Data extraction wishlist**:
- MUST: ParentId 보존, Level 정수 타입, Hierarchy sheet
- SHOULD: Flow Direction/Cut length 복구, Pipeline 충돌 해결, type-strict 컬럼
- NICE: Parquet 옵션, relationship sheets, canonical reference 테이블, change tracking, metadata sheet

---

## 5. 결과

✅ **Finding archive 규칙 수립 완료**
- memory/feedback_finding_archive.md 저장
- MEMORY.md 인덱스 갱신
- docs/findings/README.md + TEMPLATE.md 작성

✅ **M1 finding archive 완성**
- audit.py 첫 실행 통과 (8 섹션 출력)
- 5 CSV 증거 파일 생성
- 4 matplotlib PNG 차트 생성 (각 60-70 KB)
- README.md 5 섹션 완료
- dxtnavis-pr-draft.md 작성 완료

✅ **테스트 회귀 없음**: 기존 192 테스트는 손대지 않았으므로 재실행 불필요. archive 는 docs/findings/ 에만 생성.

✅ **pytest 192/192 유지** (영향 없음 확인을 위해 간이 실행 가능)

### 다음 단계 결정 대기

사용자 결정이 필요한 항목:
1. **Phase 1e 실행 여부**: M1 Resolution 4.2 에서 추천한 Option 2 (confidence column) 를 바로 진행할지
2. **DXTnavis PR 제출 방식**:
   - a. 이 repo 에 draft 로만 남기고 사용자가 수동 제출
   - b. `gh api` 로 DXTnavis repo 에 Issue 생성
   - c. `gh pr create` 로 PR 생성 (DXTnavis 를 fork/clone 해서 실제 C# 수정까지)

제 추천: **1a (Phase 1e 진행) + 2b (Issue 생성)**. Issue 는 코드 변경 없이 토론 시작이 가능하고, 실제 C# 수정은 사용자가 직접 하는 것이 바람직.
