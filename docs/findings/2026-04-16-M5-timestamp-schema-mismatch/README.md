# 2026-04-16 — M5 — palantir-sdk `write_pandas` 가 Timestamp 를 Parquet DATE 로 직렬화

**발견 일자**: 2026-04-16
**해결 일자**: 2026-04-16 (same-day rollback)
**Severity**: 🟠 MAJOR
**Status**: ✅ **Resolved** (D-AIFDE-7 rollback via `fix_dataset_schema.py`; String 복귀)
**Discovered by**: BimPiping Object Type 등록 중 Foundry UI 의 Dataset Preview 탭 에러
**Affects**: Foundry 8 datasets 전수 (6 Object Type + 2 aggregate), Spark-backed reader, UI Preview

---

## 1. 현상 (Symptom)

2026-04-16 오후, AI FDE Round 5 단계 에서 BimPiping Object Type 을 Foundry 에 등록한 직후, **Dataset → Data Preview** 탭 에서 다음 에러로 레코드 렌더링 실패:

```
org.apache.spark.sql.execution.datasources.SchemaColumnConvertNotSupportedException
column: [ingested_at_utc]
physicalType: INT64
logicalType: date
```

동일 에러가 `foundry-sdk` 의 `Dataset.read_table(..., format="ARROW")` 경로 에서도 재현됨 (Spark 을 거치는 모든 읽기 경로).

**영향 매트릭스**:

| 소비 경로 | 결과 | 이유 |
|---|:-:|---|
| Foundry Dataset Preview UI | ❌ FAIL | Spark schema validation 실패 |
| `foundry-sdk read_table` (ARROW) | ❌ FAIL | 동일 Spark 경로 |
| Ontology Object Type 생성 (UI wizard) | ✅ OK | 스키마 메타데이터 읽기 only — 레코드 스캔 미발생 |
| Ontology SDK 쿼리 (`objects().BimPiping()`) | ✅ OK | Ontology API 는 별도 serving path |
| Pipeline Builder 로 read | ❓ 미검증 | 영향 범위 밖 (사고 시점 에서는 빠른 복구 우선) |

**정량 영향**: Foundry 상의 BIM-KG 프로젝트 **8 datasets 전수** 가 broken 상태 (BimPiping 등록 이후 다른 5 Object Type + 2 aggregate 까지 동일 파이프라인 이 었기 때문).

## 2. Evidence

**Spark 에러 원문**: [`evidence/spark_error_original.txt`](evidence/spark_error_original.txt) — Dataset Preview 의 stacktrace 전문.

**Parquet schema 비교** (`pyarrow.parquet.read_schema` 기반):

| Dataset | Local parquet `ingested_at_utc` | Foundry 사고 후 (cast 결과) | Foundry 복구 후 |
|---|---|---|---|
| bim_piping | `string` | `date (INT64)` ❌ | `string` ✅ |
| bim_structural | `string` | `date (INT64)` ❌ | `string` ✅ |
| bim_equipment | `string` | `date (INT64)` ❌ | `string` ✅ |
| bim_electrical | `string` | `date (INT64)` ❌ | `string` ✅ |
| bim_hvac | `string` | `date (INT64)` ❌ | `string` ✅ |
| bim_other | `string` | `date (INT64)` ❌ | `string` ✅ |
| bim_pipelines | `timestamp[ns, tz=UTC]` | `date (INT64)` ❌ | `string` ✅ |
| bim_piperuns | `timestamp[ns, tz=UTC]` | `date (INT64)` ❌ | `string` ✅ |

전체 상태 표: [`evidence/schema_state_before_after.csv`](evidence/schema_state_before_after.csv).

**감사 스크립트**: [`audit.py`](audit.py) — 8 datasets 의 local parquet 을 스캔하여 `ingested_at_utc` 물리/논리 타입을 DataFrame 으로 보고. 기대값과 불일치 시 `mismatch=True` 플래그.

**시각화**: [`figures/impact_timeline.png`](figures/impact_timeline.png) — 2026-04-15 오전 (String, working) → 2026-04-15 오후 (cast 후 DATE, broken) → 2026-04-16 (복구 후 String, working) 8 datasets 별 타임라인.

## 3. Root Cause

`scripts/cast_timestamp_columns.py` (D-AIFDE-7 결정 의 구현) 가 6 Object Type dataset 을 foundry-sdk 로 읽고 `pd.to_datetime(..., utc=True)` 로 `datetime64[ns, UTC]` 캐스팅 후 **palantir-sdk 의 legacy `Dataset.write_pandas()`** 로 재업로드 — 이때 palantir-sdk 가 pandas datetime 을 Parquet 파일 에 **DATE logical type (INT64 physical)** 으로 직렬화. 기대 했던 TIMESTAMP(MICROS/NANOS) logical 이 아님.

Spark reader 는 테이블 스키마 (Foundry 메타데이터) 가 Timestamp 라고 기대 하는데 실제 Parquet physical INT64/logical DATE 을 만나서 `SchemaColumnConvertNotSupportedException` 를 던짐. 이것이 UI Preview 실패의 직접 원인.

**이유 요약**:

1. palantir-sdk `write_pandas` 의 dtype → Parquet mapper 가 tz-aware pandas datetime 을 Date 로 narrow 하는 알려진 버그 (또는 미지원 path)
2. 같은 SDK 로 String 을 쓰는 경로 는 이 문제 발생 X — **String-only 가 알려진-정상 경로**
3. Ontology API 는 Parquet physical 을 거치지 않고 Foundry 내부 serving layer 를 사용하므로 영향 없음 → 등록 자체는 성공했던 이유

### 3.1 왜 이전에 발견 안 됐는가

- Phase 2 등록 직후 SDK 쿼리 만 검증 했고 UI Preview/Spark path 는 smoke-test 범위 밖 이 었음
- `foundry-sdk read_table` 검증 을 cast 직후 실행 했다면 즉시 잡혔을 상황
- `cast_timestamp_columns.py` 의 로컬 dry-run (pandas 만 찍어 보기) 은 통과 했지만 Foundry Parquet round-trip 은 놓침

### 3.2 왜 범위가 8 datasets 전수 인가

- D-AIFDE-7 원 스크립트 는 6 Object Type 만 대상 이었지만, 복구 스크립트 `fix_dataset_schema.py` 는 **2 aggregate dataset 도 동일 증상** 을 확인 (local parquet 에 이미 datetime 이 들어 있음 → 같은 write_pandas path 로 업로드 되면 동일 버그). 따라서 복구 대상 을 8 로 확장.

## 4. Resolution

### 4.1 접근: String 으로 전수 복귀

[`scripts/fix_dataset_schema.py`](../../../scripts/fix_dataset_schema.py) 를 작성 해 8 datasets 를 다음 과 같이 재업로드:

1. 모든 datetime / date dtype 컬럼 → ISO 8601 String (NaT → 빈 문자열)
2. palantir-sdk 의 string-path 가 known-working 이므로 타입 downgrade 하여 안전 복구
3. 업로드 후 5 초 대기 → `foundry-sdk read_table` 로 verification 루프 자동 수행

**Trade-off** (D-AIFDE-18 에서 평가):

| Option | 선택 | 이유 |
|---|:-:|---|
| A. String 복귀 (D-AIFDE-7 rollback) | ✅ | Phase 2 blocker 해소 최우선, time-series query 미사용 |
| B. pyarrow 로 명시 Timestamp(us, tz=UTC) 재업로드 | ❌ | palantir-sdk 버그 회피 우회로 — 재발 가능 |
| C. Pipeline Builder 로 파생 dataset | 🔭 | D-AIFDE-13 원칙 상 정답 이지만 Phase 3 으로 이관 |

### 4.2 검증 결과

`fix_dataset_schema.py` 실행 후:

- 8 datasets 의 `ingested_at_utc` 모두 `string` 으로 복귀
- Foundry UI Dataset Preview: ✅ 정상 렌더링
- `foundry-sdk read_table` (ARROW): ✅ 정상
- Ontology SDK 쿼리: ✅ (기존에도 정상 이었고 변동 없음)

### 4.3 Follow-up (미해결 잔여 항목)

| # | 항목 | 담당 | 상태 |
|---|---|---|:-:|
| 1 | Ontology property `ingestedAtUtc` type 을 Date → String 으로 UI 수정 | 사용자 (Foundry UI) | 🟡 Open (UI 에서 type mismatch flag 됨) |
| 2 | Pipeline Builder 로 timestamp 파생 dataset 생성 (Phase 3 operational layer) | Phase 3 | 🔭 Deferred |
| 3 | `cast_timestamp_columns.py` 아카이브/경고 주석 (재실행 금지) | 이번 finding 으로 대체 | ✅ Resolved via README cross-ref |

## 5. Prevention (재발 방지)

### 5.1 Governance: D-AIFDE-13 이 이미 답을 내렸다

이 사건 이 **D-AIFDE-13 (Raw data 불변 + Pipeline Builder 의무)** 원칙 수립의 trigger 였음:

- Raw dataset 의 in-place 수정은 금지 — palantir-sdk `write_pandas` 직접 호출 방식은 이 원칙에 의해 이미 deprecated
- Timestamp 변환과 같은 derived column 작업은 **Pipeline Builder 의 derived dataset** 으로 처리 (immutable raw + versioned derivation)
- 복구 스크립트 `fix_dataset_schema.py` 도 엄밀히 raw 를 재수정 하므로 D-AIFDE-13 위반 이지만, **emergency fix** 라는 예외로 수용 (이후 재발 시 Pipeline Builder 로 해결)

### 5.2 Process: CI 가드 와 회귀 테스트

- `fix_dataset_schema.py` 의 verification loop 를 표준화 해 모든 업로드 이후 `read_table(..., format="ARROW")` 로 round-trip 검증
- Phase 3 에서 Pipeline Builder 기반 timestamp cast 파이프라인 을 수립 시, palantir-sdk 직접 write 경로 를 **인프라 레벨 에서 금지** (role-based permission)

### 5.3 Docs

- [`docs/reference/palantir-sdk-dtype-compatibility.md`](../../../docs/reference/palantir-sdk-dtype-compatibility.md) 에 "datetime → Parquet DATE 버그" 섹션 추가 (예정)
- D-AIFDE-18 session log 에 이 finding 을 cross-ref

## 6. References

- **재현 스크립트**: [`audit.py`](audit.py) — 로컬 parquet 8 개 의 `ingested_at_utc` 타입 대조
- **증거**:
  - [`evidence/spark_error_original.txt`](evidence/spark_error_original.txt) — Spark stacktrace 원문
  - [`evidence/schema_state_before_after.csv`](evidence/schema_state_before_after.csv) — 8 datasets × 3 상태 (원본 / broken / 복구)
- **시각화**: [`figures/impact_timeline.png`](figures/impact_timeline.png)
- **원인 스크립트 (재실행 금지)**: [`scripts/cast_timestamp_columns.py`](../../../scripts/cast_timestamp_columns.py)
- **복구 스크립트**: [`scripts/fix_dataset_schema.py`](../../../scripts/fix_dataset_schema.py)
- **관련 Decision**:
  - D-AIFDE-7: String → Timestamp cast 8 datasets — 이 finding 의 rollback 대상
  - D-AIFDE-13: Raw data 불변 + Pipeline Builder 의무 — 이 finding 이 배경
  - D-AIFDE-18: ingested_at_utc Spark 읽기 에러 triage — 이 finding 의 모체
- **AI FDE session log**: [`docs/analysis/ai-fde-sessions/2026-04-15-phase2-ontology-modeling.md`](../../analysis/ai-fde-sessions/2026-04-15-phase2-ontology-modeling.md) §D-AIFDE-18
- **상위 맥락**: [`docs/PROJECT-JOURNAL.md`](../../PROJECT-JOURNAL.md) §3 M5
