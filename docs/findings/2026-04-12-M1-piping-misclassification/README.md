# 2026-04-12 — M1 — Piping misclassification via XLSX substring matching

**Severity**: 🟠 MAJOR
**Status**: ✅ **Fully Resolved** (Upstream PR #3 applied locally + re-baselined to 2026-04-12)
**Discovered by**: Phase 1 verification audit (semantic deep dive)
**Affects**: All Phase 1 downstream outputs containing `refined_class='Piping'`

---

## 1. Finding

DXTnavis 의 `RefinedXlsxExporter.InferClass` 가 **word boundary 없는 substring 매칭** 을 사용하여,
구조/전기 객체를 Piping 으로 오분류합니다.

**정량 영향**:
- 전체 XLSX Piping: **4,014 개**
- HIGH confidence (pipeline + commodity/spec/npd 메타): **2,926 개** ✅
- LIKELY_BUG (pipeline 도 metadata 도 없음): **997 개** 🔴
- Piping 클래스가 약 **+34% 부풀려짐** (2,926 → 4,014)

**구체 증거**:
- `MemberSystem-1-0151` — system path: `"Electrical Device > Steel > MemberSystem"`.
  Piping 키워드 `tee` 가 "s-**TEE**-l" 부분 문자열로 매치 → Piping 분류.
  실제로는 Structure/Electrical.
- `Cable Tray Part` × 25, `Cableway Feature` × 15 — sys_path 에 "Pipe Rack" 포함 → Piping.
  실제로는 Electrical.
- `Pipe Trenches` × 21 — 콘크리트 trench 구조물 → Structure 이어야 함. `pipe` 키워드 매치 → Piping.

## 2. Evidence

### 2.1 Reproducible audit

```bash
.venv/bin/python docs/findings/2026-04-12-M1-piping-misclassification/audit.py
```

이 스크립트는 아래 CSV 4개를 `data/` 에 생성합니다.

### 2.2 Data artifacts

| 파일 | 내용 |
|------|------|
| `data/piping_confidence_breakdown.csv` | 4 rows — Piping 4,014 을 HIGH/MED/LOW/LIKELY_BUG 로 분해 |
| `data/substring_bug_causes.csv` | 4 rows — 키워드별 false positive 원인과 건수 |
| `data/likely_misclassified_sample.csv` | Top 20 display_name prefix 중 LIKELY_BUG 소속 |
| `data/keyword_hit_debug.csv` | 8 rows — 각 Piping 키워드가 어떤 substring 에 매치되는지 |
| `data/structure_sanity_check.csv` | Structure 클래스에 cross-contamination 없음 증명 (sp3d_pipeline = 0, sp3d_eqp_type_0 = 0) |

### 2.3 Visualizations

**Figure 1 — Piping confidence breakdown**

![01_piping_confidence](figures/01_piping_confidence.png)

2,926 HIGH (신뢰 가능) vs 997 LIKELY_BUG (오분류 의심).

**Figure 2 — Substring bug causes**

![02_substring_bug_causes](figures/02_substring_bug_causes.png)

- `Pipe Rack` 폴더명 → 698 건 (`pipe` 키워드 매치)
- `Pipe Trench` 폴더명 → 60 건
- `Pipeline` 폴더명 → 12 건
- `steel` substring → `tee` 매치 → 10 건

**Figure 3 — Top 15 display_name prefixes in LIKELY_BUG**

![03_likely_misclassified](figures/03_likely_misclassified.png)

`MemberSystem` (185), `MemberPartPrismatic` (185), `Geometry` (83),
`Insulation Volume` (83), `HgrProfile` (60), `Cover` (38),
`Pipe Trenches` (21), `Refining Pipe Rack` (17) 등.

**Figure 4 — Class distribution inflation**

![04_class_distribution](figures/04_class_distribution.png)

XLSX 4,014 vs 실제 Piping 2,926. 차이 1,088 건이 questionable.

## 3. Analysis

### 3.1 Root cause

`DXTnavis/Services/RefinedXlsxExporter.cs` 의 `InferClass` 메서드 (line 298-375):

```csharp
string combined = (sysPath + " " + displayName).ToLowerInvariant();
foreach (var key in objData.Keys)
{
    if (key.StartsWith("__")) continue;
    combined += " " + key.ToLowerInvariant();
}

if (combined.Contains("pipe") || combined.Contains("valve") ||
    combined.Contains("flange") || combined.Contains("elbow") ||
    combined.Contains("tee") || ...)
    return "Piping";
```

문제:
1. **`.Contains()` 는 substring 매칭** — word boundary 고려 없음
2. `"tee"` 키워드가 `"steel"` 부분 문자열로 매치됨 (s-**tee**-l)
3. `"pipe"` 키워드가 폴더명 `"Pipe Rack"`, `"Pipe Trench"`, `"Pipeline"` 에 매치됨
4. Piping 이 Tier 3 에서 첫 번째로 평가되므로 이런 false positive 가 Structure 나 Electrical 분류보다 우선함
5. **속성 키 이름** 까지 검색 대상에 포함되어 의도치 않은 매치 빈발

### 3.2 Impact

| Downstream phase | 영향 |
|-----------------|------|
| **Phase 1a Gold** | `bim_objects_enriched.parquet` 의 `refined_class = 'Piping'` 4,014 중 997 개가 잘못됨 |
| **Phase 1d PowerBI** | `fact_objects.csv` 의 class 분포 부정확; `dim_class.csv` Piping 카운트 4,014 로 과대계상 |
| **Phase 1d Foundry** | `ontology/2026-04-07/object_types/piping.parquet` 4,014 행 중 997 행 misclassified |
| **Phase 2 Ontology** | `PipingComponent` Object Type 정의 시 997 개가 포함되어 type mismatch 유발 |
| **Phase 4 Analytics** | 파이프 구조 그래프 분석 결과 왜곡 (실제 pipe 아닌 객체가 포함) |
| **Phase 5 LLM** | "파이프 몇 개?" 질의에 4,014 답변 → 사용자가 1,088 개 중 어떤 것이 진짜인지 분별 불가 |

### 3.3 Related known issues

- `docs/analysis/refined-xlsx-exporter-logic.md` §4.3 — "Substring 기반, word-boundary 없음" 을 로직 분석 시 이미 인지했음. 당시에는 영향 범위를 정량화하지 않음.
- `docs/analysis/phase-1-verification-findings.md` A1 — "Pipelines 라벨 153 건" 은 이 버그의 하위 증상.
- XLSX oracle 테스트 100% 통과 → Python 포팅은 올바름. 버그는 원천 C# 에 있음.

## 4. Resolution

### 4.1 Options considered

| Option | 접근 | 장점 | 단점 | 시간 |
|--------|------|------|------|------|
| **1. Accept** | 현재 상태 수용, Phase 2 에서 필터 | 현 코드 불변 | 기술 부채 Phase 2 로 이월 | 0일 |
| **2. Phase 1e confidence column** | `classification_confidence` 컬럼 추가 | 명시적, 테스트 가능, Phase 2 에서 필터링 자유 | Phase 1d 재실행 필요 | 0.5일 |
| **3. Python classifier override** | Python 포팅을 수정 | 정확한 분류 | Oracle contract 깨짐, C# 와 동기 깨짐 | 1일 |
| **4. DXTnavis 원천 수정 + 재생성** | C# InferClass 수정 후 XLSX 재 export | 원천 해결, 모든 프로젝트 혜택 | C# 수정 + 재export 필요 | 1-2일 |

### 4.2 Selected approach

**Option 2 (Phase 1e confidence column) + Option 4 (DXTnavis PR)** 병행.

**근거**:
1. Option 2 는 현재 repository 에서 즉시 적용 가능하고 Phase 2 를 언블록함
2. Option 4 는 장기적으로 올바른 해결이지만 C# 작업 + 사용자 재 export 필요
3. 두 개가 병행되면 단기 (confidence) 와 장기 (원천) 모두 커버

### 4.3 Action items

- [x] Phase 1e: `src/bimkg/ingest/clean.py` 에 `classification_confidence` 파생 컬럼 추가
- [x] Phase 1e: 테스트 작성 — HIGH 2,926 / LOW 91 / LIKELY_BUG 997 카운트 검증 (18 신규 테스트)
- [x] Phase 1e: Gold 테이블 + Phase 1d 산출물 재생성 (216 → 218 cols)
- [x] Phase 1e: `phase-1e-confidence-layer.md` task log 작성
- [x] DXTnavis Issue: [Issue #2](https://github.com/tygwan/DXTnavis/issues/2) 생성 완료
- [x] DXTnavis PR #3 open & verified — [PR #3](https://github.com/tygwan/DXTnavis/pull/3)
- [x] 새 XLSX snapshot 2026-04-12 획득 — `Refining_ObjectID_20260412_064240.xlsx`
- [x] Python xlsx_classifier.py 에 negative lookahead regex 적용
- [x] Oracle 테스트 12,009/12,009 재검증 (100% 일치)
- [x] `config.SNAPSHOT = "2026-04-12"` 갱신
- [x] `run_phase_1a()` + Phase 1d exporter 재실행 완료
- [x] 테스트 pinned counts 전면 갱신 (212 tests passing)
- [x] `classification_confidence` 재평가 — 유지 (136 LIKELY_BUG 가 여전히 존재하므로 가치 있음)
- [ ] Phase 2: `PipingComponent` Object Type 구축 시 `classification_confidence = 'HIGH'` 만 포함 (Phase 2 재개 시 적용)

### 4.4 Resolution commit

**Phase 1: Local mitigation (2026-04-12)**: Phase 1e 에서 `classification_confidence` + `classification_confidence_reason` 2개 컬럼을 Gold 테이블, PowerBI fact_objects, 모든 Foundry Object Type parquet 에 추가.
- 커밋: `6a337e0`
- 검증: 210/210 tests passing (18 Phase 1e 신규 포함)
- 결과: Piping 4,014 분해 — HIGH 2,926 / LOW 91 / LIKELY_BUG 997
- 원인별 LIKELY_BUG 분포 (2026-04-07):
  - `piping_no_metadata_pipe_rack_folder`: 698
  - `piping_no_metadata_pipe_trench_folder`: 60
  - `piping_no_metadata_pipeline_folder`: 12
  - `piping_no_metadata_steel_tee_substring`: 10
  - `piping_no_metadata_unknown`: 217

**Phase 2: Upstream fix + re-alignment (2026-04-12)**: DXTnavis PR #3 적용 후 2026-04-12 snapshot 으로 전면 재정렬.
- DXTnavis PR #3: https://github.com/tygwan/DXTnavis/pull/3 (open, mergeable, verified)
- 새 XLSX: `Refining_ObjectID_20260412_064240.xlsx` (PR #3 regex 적용됨)
- Python xlsx_classifier.py 업데이트: `PIPING_REGEX` (negative lookahead) + 5 개의 다른 `*_REGEX` 모두 word-boundary 기반
- Oracle 재검증: 12,009 / 12,009 = **100% 일치** (첫 시도)
- Phase 1a/1d 재실행 완료
- 테스트: **212/212 passing** (210 → 212, +2 new)
- 결과: Piping 3,062 분해 — HIGH 2,926 / LOW 0 / LIKELY_BUG 136
- 원인별 LIKELY_BUG 분포 (2026-04-12):
  - `piping_no_metadata_unknown`: 128 (Tier 2 Piping w/o metadata, 대부분 legit)
  - `piping_no_metadata_pipe_rack_folder`: 8 (잔여 — Tier 2 로 통과한 객체)
  - `piping_no_metadata_pipe_trench_folder`: 0 (완전 해결)
  - `piping_no_metadata_pipeline_folder`: 0 (완전 해결)
  - `piping_no_metadata_steel_tee_substring`: 0 (완전 해결)

**Class 분포 변화** (2026-04-07 → 2026-04-12):

| Class | 04-07 | 04-12 | Δ | 해석 |
|-------|------:|------:|---:|------|
| Piping | 4,014 | 3,062 | -952 | 잘못 분류된 것들 제거 |
| Structure | 5,926 | 4,840 | -1,086 | 일부가 Electrical/HVAC/Other 로 이동 |
| Other | 697 | 2,159 | +1,462 | Pipe Rack/Trench 들이 여기로 |
| Electrical | 449 | 1,053 | +604 | 제대로 분류된 cable/conduit |
| HVAC | 72 | 125 | +53 | 제대로 분류된 duct |
| Equipment | 851 | 770 | -81 | 일부가 Other 로 |
| **Total** | 12,009 | 12,009 | 0 | ObjectId 100% 동일 |

**Source fix (external)**: [DXTnavis Issue #2](https://github.com/tygwan/DXTnavis/issues/2) → [PR #3](https://github.com/tygwan/DXTnavis/pull/3) (2026-04-11 제출, open/mergeable).

**Deprecation path**: DXTnavis PR #3 merge + XLSX 재생성 완료되면 Phase 1e 의 confidence column 은 deprecation 가능 (모든 Piping 이 HIGH 가 되므로).

---

### 4.5 PR #3 feedback — 제안한 fix 가 불완전했음 (2026-04-12 접수)

DXTnavis 측에서 Issue #2 에 제시된 `\b...\b` 패턴을 실제 적용 후 검증한 결과, **클래스 분포 변화 0 건** — 즉 fix 가 전혀 작동하지 않음.

#### 원인 분석

제안했던 패턴:
```csharp
@"\b(pipe|valve|flange|elbow|tee|reducer|nozzle|coupling)\b"
```

`Pipe Rack` 같은 **composite noun** (공백으로 분리된 두 단어) 에서:
- `\bpipe\b` 에서 `\b` 앞뒤는 각각 공백/시작, 공백/word-boundary → **여전히 매치됨**
- 즉 `pipe` 는 `"Pipe Rack"` 의 `Pipe` 부분에서 여전히 단어 경계로 인식됨
- 기존 `.Contains("pipe")` 와 동일한 동작

**나의 오류**: `\b` 의 semantic 을 "composite noun 단위" 로 착각. 실제로는 `\b` 가 알파벳과 공백/기호 사이의 전환만 감지하므로, 공백 분리된 구조물 명사는 여전히 매치됨.

#### 올바른 fix (PR #3)

```csharp
@"\b(pipe(?!\s+(rack|trench|support|way|bridge|shoe))|valve|flange|elbow|tee|reducer|nozzle|coupling)\b"
```

**Negative lookahead** `(?!\s+(rack|trench|support|way|bridge|shoe))` 가 `pipe` 매치 후 뒤에 구조물 명사가 오는 경우를 거부.

효과:
- "Pipe Rack" → 매치 안 됨 (rack 이 뒤에 옴)
- "Pipe Trench" → 매치 안 됨
- "Pipe-1-0042" → 매치됨 (뒤에 `-1-0042`, 공백+명사 패턴 아님)
- "90 Degree Direction Change" → 매치 안 됨 (애초에 pipe 단어 없음)

#### Snapshot drift 발견 — 우리 baseline 과 다른 클래스 분포

DXTnavis PR #3 검증은 **2026-04-12 snapshot** 기준인데, 우리 baseline (2026-04-07) 과 숫자가 크게 다름:

| Class | 2026-04-07 (우리) | 2026-04-12 buggy | 2026-04-12 fixed |
|-------|------------------:|-----------------:|-----------------:|
| Piping | **4,014** | 3,903 | 3,062 |
| Structure | **5,926** | 4,448 | 4,840 |
| Other | **697** | 1,758 | 2,159 |
| Electrical | **449** | 1,008 | 1,053 |
| HVAC | **72** | 122 | 125 |
| Equipment | **851** | 770 | 770 |
| Total | 12,009 | 12,009 | 12,009 |

**관찰**:
- 총 객체 수는 동일
- 클래스 분포는 대폭 재배치
- 2026-04-07 ≠ 2026-04-12 (even before the fix)
- 이는 **원천 SP3D 모델 변경** 또는 **DXTnavis 버전/파라미터 변경** 의 증거

**함의**:
- 우리가 Phase 2 재개 시 2026-04-12 (또는 더 나중) snapshot 을 받아야 함
- Expected counts 가 변경되므로 **우리의 모든 test 가 count 재조정 필요**
- 2026-04-07 baseline 은 historical 로만 보관

#### 153 "Pipelines" 라벨 객체는 실제로는 올바름

제가 M1 finding 초기 분석에서 "가짜 Pipeline 라벨" 이라고 의심했던 153 개 객체가 실은:

- Tier 3 substring 매칭이 아닌 **Tier 2 property key 매칭** 으로 Piping 분류됨 (`SmartPlant 3D|Pipeline` 키 존재)
- Spot check: `90 Degree Direction Change-3114`, `Concentric Size Change-1001`, `Flange-2101` 같은 **실제 배관 피팅**
- `sp3d_pipeline = "Pipelines"` 값은 placeholder 지만, 객체 자체는 진짜 배관 컴포넌트
- 따라서 이 153 건은 **Piping 이 정답**. 분류 버그가 아님

**우리의 Phase 1e 구현 영향**: `classification_confidence_reason = "piping_no_metadata_pipeline_folder"` 로 분류한 12 건 (또는 유사한 것) 을 재검토해야 함. 실제로는 HIGH 가 될 가능성 있음.

#### PR #3 실제 적용 결과

| Class | Before (buggy) | After (fixed) | Δ |
|-------|---------------:|--------------:|---:|
| Piping | 3,903 | **3,062** | -841 |
| Structure | 4,448 | **4,840** | +392 |
| Other | 1,758 | **2,159** | +401 |
| Electrical | 1,008 | 1,053 | +45 |
| HVAC | 122 | 125 | +3 |
| Equipment | 770 | 770 | 0 |

**회귀 검증**: 파이프라인 속성 가진 2,773 객체 → 100% 여전히 Piping (leakage 0)

**Pipe Rack 분석** (898 객체):
- Piping 890 → 109 (109 는 랙 내부의 실제 피팅으로 검증)
- Structure +392, Other +341, Electrical +45, HVAC +3

#### Python port 영향 분석

우리의 `xlsx_classifier.py` 가 **PR #3 패치를 동일하게 반영** 해야 함:

```python
# Current (incorrect)
PIPING_KEYWORDS: tuple[str, ...] = (
    "pipe", "valve", "flange", "elbow", "tee", "reducer", "nozzle", "coupling",
)
# Matches via: any(kw in combined for kw in PIPING_KEYWORDS)

# Proposed new implementation
import re

PIPING_REGEX = re.compile(
    r"\b(pipe(?!\s+(rack|trench|support|way|bridge|shoe))"
    r"|valve|flange|elbow|tee|reducer|nozzle|coupling)\b",
    re.IGNORECASE,
)
# Matches via: PIPING_REGEX.search(combined) is not None
```

이와 함께:
- `test_oracle_100_percent_agreement` 는 새 snapshot 기준으로 재검증
- `classification_confidence` 로직의 count 가 변경됨 (현재: HIGH 2,926 / LIKELY_BUG 997 → 변경 예상)
- 모든 Gold parquet 재생성 + Phase 1d exporter 재실행
- Phase 1e 테스트의 pinned count 갱신

#### 재개 체크리스트 업데이트 (D11 보완)

- [ ] DXTnavis PR #3 merge ← **user action**
- [ ] DXTnavis 의 release / publish (필요 시)
- [ ] **새 XLSX snapshot export** (2026-04-12 또는 최신)
- [ ] `data/raw/dxtnavis/<new-date>/` 에 새 raw 파일 배치
- [ ] `bimkg.config.SNAPSHOT` 상수 갱신
- [ ] **Python classifier 업데이트**: regex negative lookahead 적용
- [ ] Oracle 테스트 재구성 (새 expected counts)
- [ ] `run_phase_1a()` 재실행 → Gold 재생성
- [ ] `classification_confidence` 컬럼 재검토 — 아마 대부분 HIGH 가 되므로 **deprecation 여부 재평가**
- [ ] Phase 1d exporter 재실행 → PowerBI/Foundry 산출물 갱신
- [ ] 전체 테스트 210+ 통과 + expected counts 모두 갱신
- [ ] Phase 2 Q2~Q8 재평가 후 재개

## 5. References

- **Source code analysis**: [`docs/analysis/refined-xlsx-exporter-logic.md`](../../analysis/refined-xlsx-exporter-logic.md)
- **Original C# source**: https://github.com/tygwan/DXTnavis/blob/main/Services/RefinedXlsxExporter.cs#L298-L375
- **Python port**: [`src/bimkg/ingest/xlsx_classifier.py`](../../../src/bimkg/ingest/xlsx_classifier.py)
- **Oracle test**: [`tests/test_ingest/test_xlsx_classifier.py::test_oracle_100_percent_agreement`](../../../tests/test_ingest/test_xlsx_classifier.py)
- **DXTnavis PR draft (internal)**: [`dxtnavis-pr-draft.md`](dxtnavis-pr-draft.md)
- **DXTnavis Issue #2**: https://github.com/tygwan/DXTnavis/issues/2
- **DXTnavis PR #3 (open, mergeable)**: https://github.com/tygwan/DXTnavis/pull/3
- **Gold data (current, 2026-04-07)**: `data/enriched/2026-04-07/bim_objects_enriched.parquet`
