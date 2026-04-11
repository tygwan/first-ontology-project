# Phase 1 Re-alignment — 2026-04-07 → 2026-04-12 snapshot

**일자**: 2026-04-12
**담당 Task**: #21 Re-alignment to 2026-04-12 snapshot
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| — | `data/raw/dxtnavis/2026-04-12/Refining_ObjectID_20260412_064240.xlsx` | 사용자가 Navisworks 에서 재 export 한 DXTnavis PR #3 fixed XLSX (5 MB) |
| — | `data/raw/dxtnavis/2026-04-12/AllProperties_20260407_184650.csv` 외 9 파일 | 2026-04-07 에서 복사 (동일 Navisworks 모델, 다른 코드 경로는 PR #3 영향 없음) |
| Markdown | `data/raw/dxtnavis/2026-04-12/README.md` | Audit trail: 어떤 파일을 왜 복사/재생성 했는지 기록 |
| Python | `src/bimkg/config.py` | `SNAPSHOT = "2026-04-12"`, `RAW_REFINING_XLSX` 새 파일명, 주석에 재정렬 근거 |
| Python | `src/bimkg/ingest/xlsx_classifier.py` | PR #3 의 negative-lookahead regex 를 Python 으로 포팅 — `PIPING_REGEX`, `_build_piping_regex()`, `PIPING_NEGATIVE_LOOKAHEAD_NOUNS` 상수, 5 개의 다른 `*_REGEX` 모두 word-boundary 기반으로 재구성 |
| Python | `tests/test_config.py` | 경로 테스트를 `SNAPSHOT` 상수 기반으로 일반화 (하드코딩 "2026-04-07" 제거) |
| Python | `tests/test_ingest/test_xlsx_loader.py` | 클래스 분포 재기준선: Structure 4840, Piping 3062, Equipment 770, Other 2159, Electrical 1053, HVAC 125 |
| Python | `tests/test_ingest/test_clean.py` | Phase 1e confidence 카운트 재기준선: HIGH 2926 (유지), LOW 0 (was 91), LIKELY_BUG 136 (was 997), bug_reason 세분화 재기준선 + 신규 `test_bug_reason_unknown_dominant` (128 건) |
| Python | `tests/test_ingest/test_exporters/test_foundry.py` | Foundry Object Type 카운트 재기준선: piping 3062, structural 4840, equipment 770, electrical 1053, hvac 125, other 2159 |
| Python | `tests/test_ingest/test_xlsx_classifier.py` | 단위 테스트 업데이트: `Beam-1-0042`/`Cable Tray-1` 형태로 word-boundary 경계 검증, 신규 `test_pipe_rack_is_not_piping` (negative lookahead contract), `XLSX_PATH = config.RAW_REFINING_XLSX` 로 하드코딩 제거 |
| Markdown | `docs/findings/2026-04-12-M1-piping-misclassification/README.md` | Status 🔄 Resolved locally → ✅ **Fully Resolved**, §4.3 action items 12 개 체크, §4.4 Phase 1/Phase 2 resolution commit 이원화, 클래스 분포 변화 표 |
| Markdown | `docs/PROJECT-JOURNAL.md` | §한눈에보기, §1 M1 row, §2 Timeline, §3 M1 finding 섹션, §5 DXTnavis external dep, §6 Q2 Resolved / Q4 Unblocked, §7 data paths, Test count progression 표 |
| — | `.gitignore` | `*:Zone.Identifier` + 루트 배치 방지 패턴 (이전 커밋 `25aeb45` 에 이미 반영) |

### 재생성된 산출물

`bimkg.config.SNAPSHOT` 을 갱신한 후 `run_phase_1a()` + `run_powerbi_export()` + `run_foundry_export()` 재실행:

| 레이어 | 위치 | 변화 |
|--------|------|------|
| Silver (clean) | `data/clean/2026-04-12/` | 신규 디렉터리 (2026-04-07 은 historical 로 보존) |
| Gold (enriched) | `data/enriched/2026-04-12/bim_objects_enriched.parquet` | 218 cols (동일), 행 재분류 |
| Gold SQLite | `data/enriched/2026-04-12/bimkg.db` | 신규 DB |
| PowerBI | `data/powerbi/2026-04-12/` | 10 CSV 재생성 |
| Ontology | `data/ontology/2026-04-12/{object_types,link_types}/` | 6 Object + 4 Link parquet 재생성 |

---

## 2. 문제

### 2.1 재정렬의 트리거

이틀 전 Phase 1e 를 완료하면서 M1 finding 을 **locally resolved** 상태로 마감했고, Issue #2 의 `\b...\b` fix 를 DXTnavis 에 제안했음. 2026-04-12 에 DXTnavis maintainer 가 PR #3 에 답변을 남기면서 다음이 드러남:

1. 제안한 `\b...\b` fix 는 **불충분** — `Pipe Rack` 같은 공백 분리 composite noun 에 여전히 매치
2. 실제 fix 는 **negative lookahead** 사용: `pipe(?!\s+(rack|trench|support|way|bridge|shoe))`
3. PR #3 적용 후 재생성된 XLSX 는 2026-04-07 snapshot 과 **클래스 분포가 크게 다름** (snapshot drift)
4. 153 개의 "Pipelines" label 객체는 실은 진짜 fittings (Tier 2 property key 매칭)

사용자가 PR #3 로 빌드된 DXTnavis 로 새 XLSX (`Refining_ObjectID_20260412_064240.xlsx`) 를 export 해서 가져왔고, 이 파일이 프로젝트 루트에 놓여 있는 상태에서 다음 결정이 필요:

- 다른 raw 파일도 2026-04-12 로 재 export 해야 하는가?
- 테스트 pinned counts 는 언제 업데이트할지?
- Phase 1e confidence column 은 여전히 필요한가?
- M1 finding 을 어떻게 마감할지?

### 2.2 초기 실수

- 프로젝트 루트에 놓인 XLSX + Windows Alternate Data Stream (`Zone.Identifier`) 파일이 의도치 않게 git 에 커밋됨 (commit `b73102f`)
- 원인: XLSX 를 raw 디렉터리로 이동하기 전에 finding doc 을 먼저 커밋한 순서 실수
- `.gitignore` 에 해당 패턴이 없어서 stage 됨
- **조치**: `git rm --cached` + 패턴 추가 후 cleanup 커밋 `25aeb45` 로 복구

---

## 3. 분석

### 3.1 다른 raw 파일은 재 export 가 필요 없음

사용자의 명시적 질문: **"지금 refining 새롭게정렬된것 가져왔는데, 다른 파일들은 영향이 없는가"**.

경험적 검증:
- 2026-04-07 과 2026-04-12 의 XLSX 를 pandas 로 로드해서 `ObjectId(GUID)`, `DisplayName`, `System Path` 컬럼을 비교
- 결과: **100% 동일** — 12,009 행, 단 `Class` 컬럼만 2,544 건 재분류
- 즉 Navisworks 의 근본 모델 (geometry, adjacency, validation, connected_groups) 은 변하지 않음. PR #3 는 오직 `RefinedXlsxExporter.InferClass` 만 수정했기 때문

**결론**: 다른 raw 파일들은 2026-04-07 의 것을 **그대로 복사** 해서 `data/raw/dxtnavis/2026-04-12/` 에 배치해도 안전. 이 decision 의 증거는 `data/raw/dxtnavis/2026-04-12/README.md` 에 audit trail 로 기록.

### 3.2 Python port 수정 방향 — Oracle 계약 유지

이전에는 Python `xlsx_classifier.py` 가 C# 구버전의 `.Contains()` substring 매칭을 1:1 미러링했음 (`any(kw in combined for kw in PIPING_KEYWORDS)`). PR #3 가 C# 측 로직을 regex 로 바꿨으므로 Python port 도 동일하게 바뀌어야 Oracle contract (`test_oracle_100_percent_agreement`) 가 새 XLSX 에 대해서도 100% 일치함.

**설계 선택**:
1. **키워드 리스트는 상수로 유지**: `PIPING_KEYWORDS`, `EQUIPMENT_KEYWORDS` 등은 그대로. 테스트 가독성과 C# 와의 symmetry 유지
2. **Regex 빌더 함수**: `_build_piping_regex()` (negative lookahead) + `_build_simple_regex()` (일반 word boundary). 모듈 import 시 1 회 컴파일
3. **PIPING_NEGATIVE_LOOKAHEAD_NOUNS** 를 별도 상수로 분리: C# PR #3 의 `pipe(?!\s+(rack|trench|...))` 와 동일하게 tuple 로 선언. 나중에 PR 에서 noun 이 추가되면 여기만 수정
4. **Tier 3 로직은 `.search()` 호출만 바꿈**: `any(kw in combined for kw)` → `REGEX.search(combined) is not None`. 외부 API (`infer_class()`) 는 불변

### 3.3 Regex word-boundary semantic 의 함정

PR #3 의 발견을 Python 에 옮기면서 word boundary 의 semantic 을 명확히 이해해야 함:

- `\b` 는 **word character** (`[A-Za-z0-9_]`) 와 non-word character 사이의 경계
- **underscore `_` 는 word character** 이므로 `Beam_Block` 에서 `\bbeam\b` 는 매치 안 됨
- **공백은 non-word character** 이므로 `Pipe Rack` 에서 `\bpipe\b` 는 매치됨
- 따라서 composite noun (`Pipe Rack`) 은 negative lookahead 없이는 방어 불가

이 semantic 을 테스트로 명문화: `test_word_boundary_rejects_underscore_compound` (`Beam_BlockExposed_All_Conc` → `Other`) 와 `test_pipe_rack_is_not_piping` (`Refining Pipe Rack` → not Piping). 두 테스트는 regex semantic 이 미래에 바뀌면 즉시 실패하도록 함.

### 3.4 Phase 1e confidence column 재평가

2026-04-07 snapshot 에서:
```
Piping 4,014 = HIGH 2,926 + LOW 91 + LIKELY_BUG 997
```

2026-04-12 snapshot 에서:
```
Piping 3,062 = HIGH 2,926 + LOW 0 + LIKELY_BUG 136
```

- HIGH 2,926 **그대로 유지** — 같은 진짜 배관 컴포넌트들
- LOW 91 → 0 — 기존 LOW 케이스 (pipeline xor metadata 둘 중 하나만) 가 새 XLSX 에서 아예 Piping 분류를 받지 못함. HVAC/Electrical/Other 로 재분류
- LIKELY_BUG 997 → 136 — 861 개가 오분류 수정으로 Piping 에서 이탈
- 잔여 LIKELY_BUG 136 은 대부분 `piping_no_metadata_unknown` (128 건) + 소수 `pipe_rack_folder` (8 건)
  - unknown 은 Tier 2 `SmartPlant 3D|Pipeline` 키가 있으나 metadata (commodity/spec/npd) 가 비어있는 legit fitting. 지속적인 검토 대상
  - pipe_rack_folder 잔여 8 은 Tier 2 로 통과한 객체로, Tier 3 의 negative lookahead 를 우회함

**결론**: confidence column 은 **삭제하지 않고 유지**. 이유:
1. LIKELY_BUG 136 는 여전히 의미 있는 부분집합 — Phase 2 에서 drill-down 대상
2. 컬럼 구조가 유지되면 2026-04-07 과의 비교 분석 가능 (historical baseline)
3. 향후 Phase 2 에서 `classification_confidence = 'HIGH'` 필터링 인터페이스가 그대로 작동

### 3.5 테스트 재기준선 전략

총 18 개 테스트가 실패함. 전부 "count 가 틀렸다" 또는 "classifier 가 다르게 행동한다" 류. 재정렬의 **의도된** 결과이므로 모두 업데이트해야 함:

| 카테고리 | 테스트 개수 | 업데이트 유형 |
|----------|-------------:|---------------|
| config 경로 | 1 | 하드코딩 "2026-04-07" → `config.SNAPSHOT` |
| XLSX loader 분포 | 6 | 클래스 count 재기준선 |
| clean confidence | 5 | Phase 1e count 재분포 |
| foundry Object Type | 6 | parquet 행 수 재기준선 |

**정확한 숫자는 어떻게 확인했는가**:
- Oracle test (`test_oracle_100_percent_agreement`) 를 먼저 통과시킴 — Python classifier 와 C# 의 일치를 보장
- 그 후 `run_phase_1a()` 를 실행해서 실제 재생성된 Gold parquet 에서 `value_counts()` 를 찍어봄
- 그 숫자를 테스트 expected 에 그대로 박음

---

## 4. 해결방안

### 4.1 실행 순서 (Path R)

1. **Raw 파일 배치**:
   - 루트에 놓인 `Refining_ObjectID_20260412_064240.xlsx` → `data/raw/dxtnavis/2026-04-12/` 로 이동
   - 2026-04-07 의 9 개 non-XLSX 파일을 2026-04-12 로 `cp` (읽기 전용 유지)
   - `data/raw/dxtnavis/2026-04-12/README.md` 작성: audit trail + 복사 근거
2. **.gitignore 패치**:
   - `*:Zone.Identifier` — WSL2 에서 Windows 에서 옮긴 파일의 ADS 제거
   - `/Refining_ObjectID_*.xlsx`, `/AllProperties_*.csv` — 루트 배치 방지
   - `git rm --cached` 로 잘못 커밋된 파일들 정리 (cleanup commit `25aeb45`)
3. **Config 업데이트**:
   - `SNAPSHOT = "2026-04-12"` (was "2026-04-07")
   - `RAW_REFINING_XLSX` 파일명 갱신
   - 주석에 재정렬 근거 기록
4. **Classifier regex 패치**:
   - `PIPING_NEGATIVE_LOOKAHEAD_NOUNS` 상수 추가
   - `_build_piping_regex()`, `_build_simple_regex()` 빌더 함수 추가
   - 6 개 `*_REGEX` 모듈 수준 컴파일
   - `infer_class()` Tier 3 루프를 regex `.search()` 로 교체
5. **Oracle 재검증**: `pytest tests/test_ingest/test_xlsx_classifier.py::test_oracle_100_percent_agreement` → 12,009/12,009 = 100% (첫 시도)
6. **재생성**: `python -c "from bimkg.ingest.sqlite_writer import run_phase_1a; run_phase_1a()"` → Silver/Gold/SQLite, 이어서 `run_powerbi_export()` + `run_foundry_export()`
7. **실측 기반 테스트 재기준선**: 전체 테스트 실행 → 18 failures → 각 failure 메시지에서 실제 값 확인 → expected 를 실제 값으로 업데이트
8. **Classifier unit 테스트 보완**:
   - `Beam_BlockExposed_All_Conc` → `Beam-1-0042` (word boundary 가 매치되는 형태)
   - `Cableway Straight` → `Cable Tray-1`
   - `test_pipe_rack_is_not_piping` 신규 (negative lookahead 검증)
9. **전체 테스트**: 212 passed (210 → 212, +2 new)
10. **M1 finding 마감**:
    - Status: 🔄 Resolved locally → ✅ **Fully Resolved**
    - §4.3 action items 12 개 체크
    - §4.4 Phase 1 (로컬 완화) / Phase 2 (원천 + 재정렬) 이원화
    - 클래스 분포 변화 표 추가
11. **PROJECT-JOURNAL 업데이트**: §한눈에보기, §1, §2, §3, §5, §6, §7 반영. Timeline + Test count progression 표에 2026-04-12 재정렬 entry 추가
12. **Task log 작성** (이 문서)
13. **단일 원자적 커밋**: 위 모든 변경을 하나의 커밋으로 묶어서 git log 에서 "재정렬 = 1 commit" 으로 보이게 함

### 4.2 리스크 관리

- **2026-04-07 artifacts 보존**: `data/enriched/2026-04-07/`, `data/powerbi/2026-04-07/`, `data/ontology/2026-04-07/` 모두 **삭제하지 않음**. Historical baseline 으로 감사/비교 가능
- **SNAPSHOT 상수 단일 source**: config.py 한 곳에서 교체 → 모든 DATA_* 경로가 자동으로 새 snapshot 아래로 가리킴
- **Oracle 테스트가 회귀 가드**: Python classifier 와 C# PR #3 간 동기화가 깨지는 즉시 `test_oracle_100_percent_agreement` 가 감지

---

## 5. 결과

✅ **pytest 212/212 전체 통과** (210 → 212, +2 신규 테스트)

```
tests/test_config.py                              3 passed
tests/test_ingest/test_unit_parser.py            44 passed
tests/test_ingest/test_xlsx_classifier.py        30 passed  ← 29 → 30 (+1 pipe_rack negative)
tests/test_ingest/test_xlsx_loader.py            30 passed
tests/test_ingest/test_clean.py                  53 passed  ← 52 → 53 (+1 unknown dominant)
tests/test_ingest/test_sqlite_writer.py          11 passed
tests/test_ingest/test_exporters/test_powerbi.py 22 passed
tests/test_ingest/test_exporters/test_foundry.py 21 passed

Total: 212 passed in 52.32s
```

✅ **Oracle 100% agreement** (Python classifier ↔ C# PR #3):
```
test_oracle_100_percent_agreement: 12,009 / 12,009 (100.0000%)
```

✅ **클래스 분포 변화** (2026-04-07 → 2026-04-12):

| Class | 04-07 | 04-12 | Δ | 원인 |
|-------|------:|------:|---:|------|
| Piping | 4,014 | 3,062 | -952 | PR #3 로 오분류 제거 |
| Structure | 5,926 | 4,840 | -1,086 | 일부가 Electrical/HVAC/Other 로 재분류 |
| Other | 697 | 2,159 | +1,462 | Pipe Rack/Trench 가 이동 |
| Electrical | 449 | 1,053 | +604 | Cable Tray 등이 올바른 클래스로 |
| HVAC | 72 | 125 | +53 | Duct 가 올바른 클래스로 |
| Equipment | 851 | 770 | -81 | 일부가 Other 로 |
| **Total** | 12,009 | 12,009 | 0 | ObjectId 100% 동일 |

✅ **Piping confidence 재분해** (2026-04-12):
```
HIGH       : 2,926  (unchanged — 진짜 배관 컴포넌트)
LOW        :     0  (was 91 — pipeline xor metadata 케이스 소멸)
LIKELY_BUG :   136  (was 997 — PR #3 로 861 제거)
  └── unknown            : 128  (Tier 2 Piping w/o metadata, 대부분 legit)
  └── pipe_rack_folder   :   8  (Tier 2 통과, Tier 3 lookahead 우회)
  └── pipe_trench_folder :   0  (완전 해결)
  └── pipeline_folder    :   0  (완전 해결)
  └── steel_tee_substring:   0  (완전 해결)
Total      : 3,062
```

✅ **M1 finding**: 🔄 Resolved locally → ✅ **Fully Resolved**

✅ **D11 재개 체크리스트 전부 충족** — Phase 2 unblock

### 다음 단계

- 사용자 판단으로 Phase 2 (OWL 온톨로지) 진입 가능. Q2~Q8 구조적 결정은 이제 안정화된 2026-04-12 snapshot 을 기반으로 재평가할 수 있음
- DXTnavis PR #3 의 upstream merge 는 여전히 pending (user action) — merge 후 release 하면 로컬 Python port 가 "이미 동기화된 상태" 가 됨
- 병행 가능 작업: Power BI Desktop 학습 (PBIP commit 전략)
