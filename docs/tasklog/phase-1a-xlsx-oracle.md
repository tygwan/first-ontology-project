# Phase 1a — XLSX Oracle Foundation (Steps 1~3)

**일자**: 2026-04-11
**담당 Task**: #2 (Phase 1a, 진행 중)
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| Markdown | `docs/analysis/phase-1a-data-realignment-design.md` | Section 7 (XLSX-Anchored Phase 1a) 추가 — 수정된 구조, 5개 Q 상태 변화, Foundry F1~F5 답변 반영 |
| Markdown | `docs/analysis/refined-xlsx-exporter-logic.md` | C# `RefinedXlsxExporter.cs` 786줄 전체 분해 — 3-tier 분류 로직, 키워드 전체 목록, 알려진 제한 (ParentId 손실 등), Python 재구현 체크리스트 |
| Python | `src/bimkg/ingest/xlsx_classifier.py` | C# `InferClass` 메서드의 1:1 Python 포팅 — `clean_display_string()`, `infer_class(properties, sys_path, display_name)` 구현 |
| Python | `tests/test_ingest/test_xlsx_classifier.py` | 29개 테스트: 단위 테스트(Tier 1/2/3 + clean_display_string) + **oracle 통합 테스트** (12,009 객체 100% 일치 검증) |

**핵심 목적**:
- XLSX 분류 결과를 신뢰하되, **재현 가능성**을 확보
- C# 바이너리 없이도 같은 분류를 Python으로 재생성 가능
- 미래에 C# 로직이 변경되어도 oracle 테스트가 즉시 드리프트 감지

---

## 2. 문제

**문제 #1**: `test_equipment_keyword_in_sys_path` 단위 테스트 실패
```
AssertionError: assert 'Equipment' == 'Piping'
```
- 테스트에 `sys_path="TRAINING\\A2\\U04\\Equipment\\Vessel-1"` 를 넣고 결과로 `Piping` 을 기대했으나 실제로는 `Equipment` 반환
- 테스트를 작성하면서 제가 직접 혼동했음 — "pipe" 키워드가 없으니 Piping 이 나올 리 없는데 잘못 기대값을 적었음

---

## 3. 분석

### 테스트 작성자 오류

C# 코드의 Tier 3 매칭 순서:
1. Piping (pipe/valve/flange/...)
2. Equipment (equipment/vessel/pump/...)
3. Structure (struct/steel/beam/...)
4. Electrical (electrical/cable/...)
5. HVAC (hvac/duct/...)
6. Instrumentation (instrument)

입력 `sys_path="TRAINING\\A2\\U04\\Equipment\\Vessel-1"`:
- `equipment` 키워드 매칭 (Tier 3 순위 2)
- `vessel` 키워드도 매칭 (같은 Tier 3 순위 2)
- Piping 키워드 없음 (첫 번째 조건 skip)
- → 반환값: `"Equipment"` (정답)

**문제는 Python/C# 로직이 아니라 테스트 자체의 기대값이 잘못됨.** 로직은 올바르게 작동하고 있었음.

---

## 4. 해결방안

테스트 케이스를 올바르게 수정:
- 기대값: `"Equipment"` (원래 `"Piping"` 이었음)
- 주석으로 의도 명확화: "equipment keyword matches → Equipment. Piping evaluated first but not present."
- 입력에서 `Vessel-1` 을 `Widget` 으로 변경 (vessel 도 EQUIPMENT_KEYWORDS 라서 중복 매칭이 발생하지 않도록)

---

## 5. 결과

✅ pytest **29/29 전체 통과** (10.53초)
```
tests/test_ingest/test_xlsx_classifier.py::TestCleanDisplayString        5 passed
tests/test_ingest/test_xlsx_classifier.py::TestTier1ExplicitClass        6 passed
tests/test_ingest/test_xlsx_classifier.py::TestTier2PropertyKeys         6 passed
tests/test_ingest/test_xlsx_classifier.py::TestTier3Keywords            11 passed
tests/test_ingest/test_xlsx_classifier.py::test_oracle_100_percent_agreement  1 passed
```

✅ **Oracle 통합 테스트 = 100% 일치**:
- AllProperties CSV 로드 (12,009 × 136)
- 각 행의 raw 속성을 `dict[str,str]` 로 변환
- XLSX 의 `DisplayName` + `System Path` 를 입력으로 사용
- Python `infer_class()` 실행 후 XLSX 의 `Class` 값과 비교
- **12,009 건 전부 일치, 0건 disagreement**

이로써 다음이 확보됨:
1. **재현 가능성**: C# 실행환경(Navisworks) 없이도 Python 으로 classification 재생성 가능
2. **Audit trail**: 향후 classification 변경 시 Python 코드의 git diff 로 추적 가능
3. **Drift detection**: C# 쪽이 변경되면 이 테스트가 즉시 실패하여 알림
4. **Ground-truth lookup table**: Phase 1a 의 `refined_class` 값을 XLSX 에서 그대로 읽어들일 정당성 확보

**다음 단계 (Step 4)**: `xlsx_loader.py` + `clean.py` + `sqlite_writer.py` 구현 → `bim_objects` 테이블 생성
