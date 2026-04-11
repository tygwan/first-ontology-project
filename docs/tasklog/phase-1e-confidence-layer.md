# Phase 1e — Classification Confidence Layer

**일자**: 2026-04-12
**담당 Task**: #16
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| Python | `src/bimkg/ingest/clean.py` | `add_classification_confidence()` 함수 + 상수 (`CONFIDENCE_HIGH/LOW/LIKELY_BUG`, `CONFIDENCE_REASONS` vocabulary) 추가. `build_bim_objects_gold()` 파이프라인에 연결 |
| Python | `src/bimkg/ingest/exporters/powerbi.py` | `FACT_OBJECTS_COLUMNS` 에 `classification_confidence` + `classification_confidence_reason` 2 컬럼 추가 (64 → 66 curated) |
| Python | `tests/test_ingest/test_clean.py` | Phase 1e 테스트 18개 추가 (`TestGoldClassificationConfidence` 11개 integration + `TestAddClassificationConfidenceUnit` 7개 pure function) |
| Python | `tests/test_ingest/test_exporters/test_powerbi.py` | `test_fact_objects_has_64_plus_1_columns` → `test_fact_objects_has_66_plus_1_columns` 로 assertion 업데이트 (65 → 67 cols) |
| Markdown | `docs/findings/2026-04-12-M1-piping-misclassification/README.md` | Status 변경 (🔄 Open → ✅ Resolved locally), §4.3 action items 체크, §4.4 resolution commit 상세 기재 |
| Markdown | `docs/PROJECT-JOURNAL.md` | §1 Quick Problem Index 에서 M1 status 업데이트, §2 Timeline 에 Phase 1e 추가, §3 Findings 에서 M1 resolution 기록 |

### Confidence Layer 의 설계

**새 컬럼 2개 추가**:
- `classification_confidence` (TEXT): `HIGH` / `LOW` / `LIKELY_BUG`
- `classification_confidence_reason` (TEXT): 9종의 controlled vocabulary

**Piping 분류 규칙**:
```
HIGH       : sp3d_pipeline 있음 AND (commodity_code OR short_code OR spec_name OR npd) 있음
LOW        : 둘 중 하나만 있음 (pipeline xor metadata)
LIKELY_BUG : 둘 다 없음 — 오분류 의심
```

**LIKELY_BUG 세부 원인**:
```
piping_no_metadata_pipe_rack_folder     - sys_path 에 "Pipe Rack" 포함
piping_no_metadata_pipe_trench_folder   - sys_path 에 "Pipe Trench" 포함
piping_no_metadata_pipeline_folder      - sys_path 에 "Pipeline" 폴더
piping_no_metadata_steel_tee_substring  - sys_path 에 "steel" (→ tee 매치)
piping_no_metadata_unknown              - 복합/중첩 경로
```

**비 Piping 클래스**: 모두 `HIGH` + `xlsx_class_clean` (cross-contamination 없음 확인됨)

### 재생성된 산출물

Phase 1e 구현 후 `run_phase_1a()` + `run_powerbi_export()` + `run_foundry_export()` 재실행:

| 파일 | 이전 | 이후 | 변화 |
|------|-----:|-----:|------|
| `bim_objects_enriched.parquet` (Gold) | 216 cols | 218 cols | +2 confidence columns |
| `bimkg.db` bim_objects table | 216 cols | 218 cols | SQLite 재생성 |
| `fact_objects.csv` (PowerBI) | 65 cols | 67 cols | +2 |
| 6 Foundry Object Type parquet | 216 cols | 218 cols | 각각 +2 |

---

## 2. 문제

작업 중 **문제 없음**. 모든 단계가 첫 실행에 통과:
- `add_classification_confidence()` 로직 첫 실행에서 정확한 HIGH 2,926 / LOW 91 / LIKELY_BUG 997 재현
- `run_phase_1a()` 재실행 정상 완료
- 18개 신규 테스트 모두 첫 실행 통과
- 기존 192 테스트 중 영향받은 것은 `test_fact_objects_has_64_plus_1_columns` 하나 (64 → 66 expected 로 업데이트)

---

## 3. 분석

### 왜 Phase 1e 가 필요했는가

M1 finding 에서 발견한 XLSX 의 substring 매칭 버그는 997 Piping 객체를 오분류함. 이 이슈의 해결 방향은 4가지 옵션이 있었음:
- Option 1: 수용하고 Phase 2 에서 필터 (기술 부채 이월)
- Option 2: Phase 1e confidence 컬럼 추가 ← **선택**
- Option 3: Python classifier 수정 (Oracle contract 파기)
- Option 4: DXTnavis 원천 수정 (시간 소요)

Option 2 + Option 4 병행 전략을 채택. Phase 1e (로컬) + DXTnavis Issue #2 (원천).

### 왜 새 컬럼 추가 방식이 최선인가

1. **Oracle contract 유지**: `refined_class` 값을 건드리지 않으므로 `test_oracle_100_percent_agreement` 깨지지 않음
2. **비파괴적**: LIKELY_BUG 객체를 삭제/숨기지 않고 **플래그** 만 추가. 향후 데이터 재검토 시 모든 원본 접근 가능
3. **명시적**: downstream 사용자는 `classification_confidence='HIGH'` 로 신뢰 가능한 부분집합 선택 가능
4. **Reversible**: DXTnavis 원천 수정되면 Phase 1e 는 deprecation 가능 (모든 Piping 이 HIGH 가 됨)
5. **Audit trail**: reason column 으로 "어떤 버그 때문에 의심되는가" 까지 추적

### 영향 받는 다운스트림

| Phase | 변화 |
|-------|------|
| **Phase 2 (OWL 온톨로지)** | `PipingComponent` Object Type 을 HIGH 2,926 만으로 구축 가능 — type mismatch 방지 |
| **Phase 3 (SHACL 검증)** | HIGH 서브셋에 대해서만 "Piping 은 pipeline 필수" 규칙 적용 → 위반 0건 |
| **Phase 4 (Analytics)** | 파이프 그래프 분석 시 HIGH 만 참여 → 왜곡 없음 |
| **Phase 5 (LLM)** | "파이프 몇 개?" 질의에 두 답변 가능: "HIGH confidence 2,926 또는 전체 4,014 (24.8% 의심)" |

### Controlled vocabulary 의 이유

`CONFIDENCE_REASONS` 상수를 tuple 로 정의하여 테스트가 값의 허용 집합을 강제. 새 reason 추가 시 상수 갱신 필수 → 실수로 typo 가 들어가면 즉시 테스트 실패로 감지됨.

---

## 4. 해결방안

### 구현 순서

1. **clean.py 상수 정의**: `CONFIDENCE_HIGH/LOW/LIKELY_BUG` + `CONFIDENCE_REASONS` 9 값
2. **`add_classification_confidence()` 구현**:
   - Default: 모든 행 HIGH + xlsx_class_clean
   - Piping 마스크 별도 처리
   - Pipeline / metadata 조합 분류
   - LIKELY_BUG 행에 대해 sys_path 기반 세부 reason 할당
   - 우선순위: Pipe Rack > Pipe Trench > Pipeline folder > steel (disjoint mask)
3. **`build_bim_objects_gold()` 에 연결**: 기존 파이프라인 (flags → si_units → lineage → title) 끝에 confidence 추가
4. **PowerBI 컬럼 추가**: `FACT_OBJECTS_COLUMNS` 에 2개 추가
5. **Smoke test**: 즉석 파이썬 스크립트로 숫자 검증 (HIGH 2926, LOW 91, LIKELY_BUG 997, bug reasons 698/60/12/10/217)
6. **테스트 작성**: 18개 (integration 11 + unit 7)
7. **Gold + 1d 재생성**: `run_phase_1a()` + `run_powerbi_export()` + `run_foundry_export()` 재실행
8. **전체 테스트**: 192 → 210 예상, 실제 210 통과 확인
9. **M1 finding Resolution 업데이트**: Action items 체크, Resolution commit 기재, status 🔄 → ✅
10. **PROJECT-JOURNAL.md 업데이트**: §1 M1 row, §2 Timeline, §3 Findings 섹션
11. **task log 작성** (이 문서)
12. **커밋 + 푸시**

### 테스트 구성

**Integration tests** (gold_objects fixture 사용):
- `test_columns_exist` — 2 컬럼 존재
- `test_confidence_values_valid` — HIGH/LOW/LIKELY_BUG 집합
- `test_confidence_reason_vocabulary` — 9 reasons 집합
- `test_piping_high_count` — 정확히 2,926
- `test_piping_low_count` — 정확히 91
- `test_piping_likely_bug_count` — 정확히 997
- `test_piping_confidence_sums_to_total` — 합 4,014
- `test_non_piping_all_high` — 비 Piping 전부 HIGH
- `test_bug_reason_pipe_rack_count` — 정확히 698
- `test_bug_reason_pipe_trench_count` — 정확히 60
- `test_bug_reason_steel_substring_count` — 정확히 10

**Unit tests** (pure function, mock DataFrame):
- `test_structure_defaults_to_high`
- `test_piping_high_with_pipeline_and_metadata`
- `test_piping_low_pipeline_only`
- `test_piping_low_metadata_only`
- `test_piping_likely_bug_pipe_rack`
- `test_piping_likely_bug_steel`
- `test_piping_likely_bug_unknown`

---

## 5. 결과

✅ **pytest 210/210 전체 통과** (59.27초, +18 신규)

```
tests/test_config.py                              3 passed
tests/test_ingest/test_unit_parser.py            44 passed
tests/test_ingest/test_xlsx_classifier.py        29 passed
tests/test_ingest/test_xlsx_loader.py            30 passed
tests/test_ingest/test_clean.py                  52 passed  ← 34 → 52 (+18)
tests/test_ingest/test_sqlite_writer.py          11 passed
tests/test_ingest/test_exporters/test_powerbi.py 22 passed
tests/test_ingest/test_exporters/test_foundry.py 21 passed
```

✅ **Gold 테이블 218 cols** (216 + 2 confidence)

✅ **Piping 세분화 재현**:
```
HIGH       : 2,926
LOW        :    91
LIKELY_BUG :   997  (698 pipe_rack + 60 pipe_trench + 12 pipeline + 10 steel + 217 unknown)
Total      : 4,014
```

✅ **비 Piping 클래스 검증**:
- Structure 5,926 — 모두 HIGH + xlsx_class_clean
- Equipment 851 — 모두 HIGH
- Electrical 449 — 모두 HIGH
- HVAC 72 — 모두 HIGH
- Other 697 — 모두 HIGH
- 합계: 7,995 HIGH 비 Piping

✅ **M1 finding status**: 🔄 Open → ✅ Resolved locally
- Resolution 4.3 action items 5/6 완료 (남은 1개: Phase 2 에서 HIGH 필터 적용)
- Resolution 4.4 resolution commit 상세 기재

✅ **PROJECT-JOURNAL.md 업데이트**: M1 row status + Timeline + Findings 섹션

### 다음 단계

Phase 1e 완료로 이 프로젝트의 Phase 1 은 완전히 **locally 해결된 상태** 가 됨.

남은 Phase 1 관련 작업:
- ⏳ DXTnavis Issue #2 응답 대기 (외부 blocking 아님, Phase 1e 로 로컬 진행 가능)
- 🎯 Phase 2 (OWL 온톨로지) 진입 준비 완료

별도 병렬 작업:
- 🎯 dev-standards repo 구축 (이 프로젝트에서 추출된 규칙들을 일반화)
