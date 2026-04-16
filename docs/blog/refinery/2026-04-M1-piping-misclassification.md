# Piping 으로 분류된 997 객체가 사실은 Structure 였던 이유

*정유시설 BIM 12,009 객체의 24.8% 를 오분류하던 substring 매칭, 그리고 upstream PR 을 두 번 만에 성공시킨 기록*

**작성일**: 2026-04-14 (최종 재정렬: 2026-04-16)
**프로젝트**: Refinery Facility Ontology Analytics
**관련 Finding**: [M1 아카이브](../findings/2026-04-12-M1-piping-misclassification/)
**태그**: 데이터 품질 · regex · word boundary · 외부 공급사 협업 · XLSX · C#/Python 포팅

---

안녕하세요. 저는 정유시설의 SP3D BIM 모델을 OWL 온톨로지와 Neo4j
지식그래프, LLM 에이전트까지 end-to-end 로 구축하는 프로젝트를 단독으로
진행하고 있습니다.

오늘 공유할 이야기는 그 프로젝트의 Phase 1 을 마무리하던 중 발견한
데이터 품질 문제, 그리고 외부 공급사 저장소에 냈던 PR 이 한 번 실패하고
두 번째 시도에 성공한 기록입니다. 엔지니어라면 한 번쯤 겪는 **substring
매칭의 함정** 과 **`\b` (word boundary) 에 대한 흔한 오해** 가 이야기의
중심에 있어요.

---

## 도입 — "뭔가 이상한데?"

Phase 1 을 마치고 Phase 2 온톨로지 설계로 넘어가기 전에, 저는 "Piping
과 Structure 의 비율이 합리적인지" 한 번 더 검증해보기로 했습니다.
12,009 객체 중 Piping 이 4,014 개, Structure 가 5,926 개. 얼핏 그럴듯한
숫자였어요.

그런데 sanity check 쿼리 하나가 이상한 결과를 뱉었습니다.

```python
piping = df[df["refined_class"] == "Piping"]
piping[piping["sys_path"].str.contains("Steel|Structure|Cable")]
# 997 rows ×
```

**Piping 으로 분류된 객체 중 997개가 system path 에 "Steel" 또는
"Structure" 또는 "Cable" 을 포함**하고 있었습니다. 전체 Piping 의 24.8%.

---

## 1차 추적 — "왜 Pipe Rack 이 Piping 이 됐을까"

몇 개를 무작위로 찍어봤습니다.

| ObjectID | display_name | sys_path | refined_class |
|----------|--------------|----------|---------------|
| `MemberSystem-1-0151` | — | `Electrical Device > Steel > MemberSystem` | **Piping** |
| `Cable Tray Part × 25` | — | `... > Pipe Rack > ...` | **Piping** |
| `Pipe Trenches × 21` | — | `Civil > Underground > Pipe Trenches` | **Piping** |

명백히 구조물이거나 전기 설비인데 Piping 으로 분류되고 있었어요.
`Pipe Rack` 은 **파이프를 받치는 철골 구조물**이고, `Pipe Trench` 는
**콘크리트 구덩이**입니다. 배관 자체가 아니라 배관을 *지지·수용*하는
시설이죠.

의심은 빠르게 좁혀졌습니다. 원인은 업스트림 분류기일 것입니다.
정유시설 BIM 데이터는 SP3D 모델에서 DXTnavis 라는 C# 도구가 XLSX 로
내보내는데, 이 XLSX 의 `refined_class` 컬럼은 DXTnavis 의 `InferClass`
메서드가 계산해요.

---

## 근원 찾기 — `InferClass` 함수까지 내려가다

DXTnavis 저장소를 열어 `Services/RefinedXlsxExporter.cs:298` 을 확인했습니다.

```csharp
string combined = (sysPath + " " + displayName).ToLowerInvariant();
foreach (var key in objData.Keys) {
    if (key.StartsWith("__")) continue;
    combined += " " + key.ToLowerInvariant();
}

if (combined.Contains("pipe") || combined.Contains("valve") ||
    combined.Contains("flange") || combined.Contains("elbow") ||
    combined.Contains("tee") || combined.Contains("reducer") ||
    combined.Contains("nozzle") || combined.Contains("coupling"))
    return "Piping";
```

두 줄이 눈에 들어왔습니다.

1. `combined.Contains("tee")` — **substring 매칭**. `"tee"` 는
   `"s**tee**l"` 의 부분 문자열입니다.
2. `combined.Contains("pipe")` — `"**Pipe** Rack"`, `"**Pipe** Trench"`,
   `"**Pipe**line"` 에 모두 매치됩니다.

즉 **`"Steel"` 이라는 단어에 `"tee"` 가 들어있기 때문에**, 철골
구조물 `MemberSystem-1-0151` 의 system path `"Electrical Device >
Steel > MemberSystem"` 이 Piping 으로 분류된 것이었어요. 공백으로
구분된 다른 단어도 마찬가지입니다. `Pipe Rack` 의 `Pipe` 는 완전한
단어지만 substring 매칭에서는 단어 경계가 의미 없습니다.

원인별로 집계해보니 이렇게 나왔습니다.

| 원인 | 건수 |
|------|-----:|
| `pipe` 매칭 on `Pipe Rack` 폴더 | **698** |
| `pipe` 매칭 on `Pipe Trench` 폴더 | 60 |
| `pipe` 매칭 on `Pipeline` 폴더 | 12 |
| `tee` 매칭 on `steel` substring | 10 |
| 기타 (metadata 없음, Tier 2 불통과) | 217 |

**합계 997**. 전체 Piping 4,014 의 24.8%. 원인도 명확하고 영향도 명확했어요.

---

## 네 개의 옵션, 그리고 선택

해결 방법을 네 가지로 정리했습니다.

| Option | 접근 | 장점 | 단점 | 시간 |
|--------|------|------|------|-----:|
| 1. Accept | 현재 상태 수용, Phase 2 에서 필터 | 현 코드 불변 | 기술 부채 이월 | 0일 |
| 2. Confidence column | `classification_confidence` 파생 컬럼 추가 | 명시적·테스트 가능 | Phase 1d 재실행 | 0.5일 |
| 3. Python override | 로컬 분류기 수정 | 정확한 분류 | Oracle contract 깨짐 | 1일 |
| 4. Upstream PR | DXTnavis C# 수정 | 원천 해결 | 외부 작업 + 재 export | 1~2일 |

저는 **2 + 4 병행**을 선택했습니다. 근거는 세 가지였어요.

- **Option 2** 는 즉시 적용 가능하고 Phase 2 를 언블록합니다.
- **Option 4** 는 장기적으로 올바른 해결이지만 외부 저장소 작업이라
  시간이 걸립니다.
- 병행하면 **단기 (confidence 신호)** + **장기 (원천 수정)** 을 모두
  커버할 수 있어요.

Option 3 (Python 만 수정) 이 매력적으로 보였지만 치명적인 단점이
있었습니다. 이 프로젝트에는 `test_oracle_100_percent_agreement` 라는
테스트가 있어요. Python 포팅이 C# 원본의 12,009 객체 분류 결과와
**100% 일치**해야 한다는 계약입니다. Python 을 먼저 고치면 이 oracle
이 깨집니다. 업스트림과 어긋난 Python 포팅은 그 자체가 또 다른 기술
부채가 되거든요.

Phase 1e 에서 `classification_confidence` (HIGH / LOW / LIKELY_BUG) 와
`classification_confidence_reason` 2 컬럼을 Gold 테이블, PowerBI
fact_objects, Foundry Object Type 전체에 추가했습니다. 18 개의 신규
테스트로 HIGH 2,926 / LOW 91 / LIKELY_BUG 997 카운트를 고정했고, 다운
스트림은 이제 선택적으로 LOW/LIKELY_BUG 를 필터할 수 있게 됐어요.

그리고 DXTnavis 저장소에 Issue #2 를 열고 PR #3 를 제출했습니다.

---

## 첫 fix 의 실패 — `\b` 의 함정

PR #3 에 제안한 패턴은 이거였습니다.

```csharp
@"\b(pipe|valve|flange|elbow|tee|reducer|nozzle|coupling)\b"
```

`\b` 는 단어 경계 (word boundary) 예요. `"steel"` 안의 `"tee"` 는
`\btee\b` 에 매치되지 않습니다 — 앞뒤가 모두 알파벳이니까요. 이것만으로
`steel → tee` 문제는 해결될 거라고 생각했습니다.

상대방이 PR 을 적용해서 XLSX 를 재생성하고 결과를 돌려줬습니다.
**클래스 분포 변화 0 건**. 전혀 작동하지 않았어요.

한참을 들여다본 끝에 제 오류를 발견했습니다.

`"Pipe Rack"` 에서 `\bpipe\b` 는 **여전히 매치됩니다**. `\b` 는 단어
문자 ↔ 비단어 문자 전환을 감지하거든요. `"Pipe Rack"` 의 `Pipe` 는:

- 앞: 문자열 시작 (word boundary ✓)
- 뒤: `P`, `i`, `p`, `e` 다음 공백 (word boundary ✓)

즉 `Pipe` 는 완전한 한 단어이고, `\bpipe\b` 는 당연히 매치됩니다.
`\b` 가 "composite noun 을 하나로 묶어준다" 는 것은 저의 착각이었어요.

엔지니어가 가끔 빠지는 구체적인 함정 하나를 그대로 밟은 셈입니다.
**"word boundary" 는 언어학적 단어가 아니라 정규식 엔진의 문자
전환** 이라는 것. `Pipe Rack` 은 두 개의 독립된 단어이고, 각각
단어 경계를 가집니다.

---

## 진짜 fix — negative lookahead

해결은 `\b` 가 아니라 **negative lookahead** 였습니다.

```csharp
@"\b(pipe(?!\s+(rack|trench|support|way|bridge|shoe))
    |valve|flange|elbow|tee|reducer|nozzle|coupling)\b"
```

`pipe(?!\s+(rack|trench|support|way|bridge|shoe))` 를 풀어 쓰면:
"`pipe` 라는 단어 다음에 공백 + (rack|trench|support|way|bridge|shoe)
중 하나가 오는 경우는 매치하지 않는다" 예요.

결과는 이렇게 나왔습니다.

| 입력 | 매치 여부 |
|------|:-:|
| `"Pipe Rack"` | ❌ |
| `"Pipe Trench"` | ❌ |
| `"Pipe Support"` | ❌ |
| `"Pipe-1-0042"` | ✅ (뒤에 `-`, 공백 아님) |
| `"Pipeline"` | ✅ (`pipe` 뒤에 `line`, 공백 없음) |
| `"90 Degree Direction Change"` | ❌ (애초에 `pipe` 없음) |

PR #3 를 업데이트하고 재검증했습니다. 이번에는 숫자가 움직였어요.

| Class | Before | After | Δ |
|-------|-------:|------:|---:|
| Piping | 3,903 | **3,062** | -841 |
| Structure | 4,448 | **4,840** | +392 |
| Other | 1,758 | **2,159** | +401 |
| Electrical | 1,008 | 1,053 | +45 |
| HVAC | 122 | 125 | +3 |
| Equipment | 770 | 770 | 0 |

회귀 검증도 깔끔했습니다. Pipeline 속성을 가진 2,773 객체는 여전히
100% Piping 분류 (leakage 0), Pipe Rack 안의 실제 배관 피팅 109개도
정상적으로 Piping 을 유지했어요.

---

## 예상치 못한 발견 — snapshot drift

상대방이 돌려준 결과를 보다가 더 큰 것을 발견했습니다. **Total 은
12,009 로 동일한데, 클래스 분포 자체가 저희 baseline (2026-04-07) 과
완전히 달랐어요.**

| Class | 2026-04-07 (우리) | 2026-04-12 buggy | 2026-04-12 fixed |
|-------|------------------:|-----------------:|-----------------:|
| Piping | **4,014** | 3,903 | 3,062 |
| Structure | **5,926** | 4,448 | 4,840 |
| Other | **697** | 1,758 | 2,159 |
| Electrical | **449** | 1,008 | 1,053 |

Fix 를 적용하기 *전에도* 분포가 바뀌어 있었습니다. 이건 **원천 SP3D
모델 자체가 변경되었거나 DXTnavis 의 export 파라미터가 변경되었다**는
증거였어요. 5일 사이에 정유시설 BIM 모델이 재분할·재분류된 것이죠.

저희 baseline 을 2026-04-12 snapshot 으로 밀어야 한다는 얘기입니다.
모든 expected count 를 갱신하고 전 파이프라인을 재실행해야 했어요.

오히려 이건 좋은 기회였습니다. PR #3 regex 를 Python 포팅에도 동일하게
적용해서, `xlsx_classifier.py` 를 업데이트했어요.

```python
# Before (buggy)
PIPING_KEYWORDS = ("pipe", "valve", "flange", "elbow", "tee", ...)
# any(kw in combined for kw in PIPING_KEYWORDS)

# After (PR #3 aligned)
PIPING_REGEX = re.compile(
    r"\b(pipe(?!\s+(rack|trench|support|way|bridge|shoe))"
    r"|valve|flange|elbow|tee|reducer|nozzle|coupling)\b",
    re.IGNORECASE,
)
# PIPING_REGEX.search(combined) is not None
```

Oracle 테스트 재실행. **12,009 / 12,009 = 100% 일치**. 첫 시도에서
바로 통과했습니다. C# 원본과 Python 포팅이 다시 동기화된 것이죠.

전체 파이프라인 재실행. 테스트 **212/212 passing**. `classification_
confidence` 컬럼은 그대로 보존했어요 — LIKELY_BUG 는 997 → 136 으로
줄었지만, 여전히 136 건이 남아있어 신호 가치가 있다고 판단했습니다.

---

## 회고 — 이 경험이 룰이 된 이유

이 하나의 finding 을 처리하면서, 저는 **같은 reflex 를 다른 finding
(M2 adjacency tier, M3 parent box) 에도 그대로 적용**하고 있다는 걸
알아차렸어요. 공통 패턴을 추출해서 dev-standards 의 **R3 Finding
Archive Rule** 로 룰화했습니다.

**5 단계 표준 프로세스**는 이렇게 구성했어요.

1. **발견** — 이상 현상 포착 (여기서는 sanity check 쿼리)
2. **재현** — `audit.py` 스크립트로 누구든 같은 숫자를 얻을 수 있게
3. **시각화** — 4 개의 PNG figure (confidence breakdown, 원인별
   분포, LIKELY_BUG top 15, class 분포 비교)
4. **결정 trace** — 4 options 비교 + 선택 근거 + 시간 trade-off
   (왜 Option 3 이 아닌 Option 2+4 인가)
5. **외부 기여** — upstream Issue + PR (단, 로컬 우회도 동시에 준비)

하나의 문제 해결이 **팀 작업 방식의 표준** 이 되는 순간이었어요.
dev-standards 저장소에 R3 이 있는 이유입니다.

---

## 엔지니어가 가져갈 것

이 경험에서 제가 배운 것들을 정리해봤습니다.

**1. substring 매칭은 word boundary 를 고려해야 합니다**
— 당연한 얘기지만 제품 코드에서 놓치기 쉬워요. `Contains()`, `in`,
`LIKE '%...%'` 모두 동일한 함정이 있습니다. 도메인 키워드를 하드
코딩할 때는 반드시 단어 경계를 같이 생각해야 해요.

**2. `\b` 는 "단어" 가 아니라 "문자 전환" 을 뜻합니다**
— `"Pipe Rack"` 의 `Pipe` 는 `\b` 기준으로 완전한 단어입니다. 공백
으로 구분된 composite noun 을 하나로 묶으려면 `\b` 만으로는 부족해요.
**Negative lookahead** 또는 **명시적 exclusion 리스트** 가 필요합니다.

**3. 외부 저장소의 버그를 고칠 때는 로컬 우회와 병행하세요**
— PR 이 언제 merge 될지 모릅니다. 그 사이에 다운스트림이 멈추면
안 돼요. Local mitigation (confidence column) 과 Upstream fix (PR) 이
동시에 달리도록 설계하는 편이 안전합니다.

**4. PR 이 실패하면 이유를 찾아 PR 을 업데이트하세요. 방어하지
않습니다**
— `\b` 가 작동할 거라는 제 가정이 틀렸을 때, 그 자리에서 잘못을
인정하고 negative lookahead 로 패턴을 다시 설계했어요. 이 과정은
PR 대화창에 그대로 남아 있습니다. 이력이 됩니다.

**5. 하나의 finding 은 다른 finding 도 드러냅니다**
— M1 을 조사하다 snapshot drift (2026-04-07 → 2026-04-12) 를 발견
했습니다. 이건 M1 의 범위 밖이었지만, baseline 갱신이 필요하다는
별도 작업으로 분기됐어요. 작업이 손대는 순간에만 드러나는 문제가
있기 마련입니다.

**6. 테스트로 숫자를 고정하면 재현성이 보장됩니다**
— HIGH 2,926 / LIKELY_BUG 136. 이 숫자를 테스트로 못박아두면 누가
파이프라인을 재실행해도 같은 결과가 나와요. dev-standards R9
(Provenance) 의 실제 적용례입니다.

---

## 참조

- **Finding archive**: [`docs/findings/2026-04-12-M1-piping-misclassification/`](../../findings/2026-04-12-M1-piping-misclassification/)
  - [`audit.py`](../../findings/2026-04-12-M1-piping-misclassification/audit.py) — 재현 스크립트
  - `figures/01~04.png` — 4 시각화
  - `data/*.csv` — 5 CSV 증거
- **재정렬 task log**: [`docs/tasklog/phase-1-realignment-20260412.md`](../../tasklog/phase-1-realignment-20260412.md)
- **XLSX classifier 로직 분석**: [`docs/analysis/refined-xlsx-exporter-logic.md`](../../analysis/refined-xlsx-exporter-logic.md)
- **DXTnavis Issue #2**: <https://github.com/tygwan/DXTnavis/issues/2>
- **DXTnavis PR #3**: <https://github.com/tygwan/DXTnavis/pull/3>
- **Python 포팅**: [`src/bimkg/ingest/xlsx_classifier.py`](../../../src/bimkg/ingest/xlsx_classifier.py)
- **dev-standards R3 (Finding Archive Rule)**: <https://github.com/tygwan/dev-standards>

---

*이 글은 dev-standards R11 실험 중 — "기록된 finding 을 기술블로그
narrative 로 풀어쓰는 패턴" 을 탐색하는 첫 번째 사례입니다. 글을
쓰며 관찰한 패턴은 [블로그 회고 메모](../blog-writing-retrospective.md)
에 정리합니다.*
