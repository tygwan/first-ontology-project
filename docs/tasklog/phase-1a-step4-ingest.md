# Phase 1a — Step 4: Ingest Implementation

**일자**: 2026-04-11
**담당 Task**: #2 (Phase 1a, 완료)
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| Python | `src/bimkg/ingest/xlsx_loader.py` | XLSX 로드 + 135 컬럼 snake_case 정규화 + 충돌 감지 |
| Python | `src/bimkg/ingest/clean.py` | Silver + Gold 빌더, 플래그 파생, SI 단위 파싱, 4-column lineage |
| Python | `src/bimkg/ingest/sqlite_writer.py` | Parquet + SQLite 출력 + `run_phase_1a()` 오케스트레이션 |
| Python | `tests/test_ingest/test_xlsx_loader.py` | snake_case, normalize_column_name, collision 탐지, XLSX 통합 테스트 |
| Python | `tests/test_ingest/test_clean.py` | Silver/Gold 테이블 무결성, 플래그 카운트, SI unit coverage, helper 단위 테스트 |
| Python | `tests/test_ingest/test_sqlite_writer.py` | `run_phase_1a()` 출력 파일 검증, SQLite readback |
| TOML | `pyproject.toml` | `pyarrow>=17.0`, `openpyxl>=3.1` 의존성 명시 |

**설계**:
- 3-layer 빌드: Silver (XLSX 단일 소스 정규화) → Gold (joins + flags + SI + lineage + title)
- Medallion 아키텍처 준수: `data/clean/` (Silver) → `data/enriched/` (Gold)
- 출력 포맷: Parquet (모든 레이어) + SQLite (Gold canonical)
- `run_phase_1a()` 단일 entry point 로 전체 파이프라인 실행

**핵심 산출물**:
- `data/clean/2026-04-07/bim_objects.parquet` (12,009 × 135)
- `data/clean/2026-04-07/bim_adjacency.parquet` (110,173 edges)
- `data/clean/2026-04-07/bim_hierarchy.parquet` (12,009 × 3)
- `data/clean/2026-04-07/bim_connected_groups.parquet` (3,355)
- `data/enriched/2026-04-07/bim_objects_enriched.parquet` (12,009 × 216)
- `data/enriched/2026-04-07/bim_adjacency_sym.parquet` (220,346 — 양방향 확장)
- `data/enriched/2026-04-07/bimkg.db` (SQLite: bim_objects + bim_adjacency)

---

## 2. 문제

**문제 #1**: `parent_id` 커버리지가 294/12,009 로 비정상적으로 낮음
- 첫 파이프라인 실행 후 검증에서 발견
- 인사이트 문서에 따르면 12,008 건이 부모를 가져야 함 (루트 1개 제외)
- validation.csv 에서 ParentId 를 조인했는데 실제로는 null 이 11,715 건

**문제 #2**: XLSX 에서 `ParentId` 컬럼이 제거되어 있음
- `RefinedXlsxExporter.cs` 의 `BuildDynamicColumns` 가 `__` 접두사 메타 키를 제외하는 로직 때문
- 대체 소스를 찾아야 함

---

## 3. 분석

`validation.csv` 의 ParentId 를 Level 별로 집계:
```
Level  total  with_parent
0          1           0
1          4           4
2        144           0
3         34           0
4        116           0
5        640           0
6       3320           0
7       4460           2
8       2968          14
9        322         274
```

Level 1 과 Level 9 에만 주로 채워져 있고 L2~L8 은 거의 비어 있다.
이건 백엔드가 **특정 계층에서만 ParentId 를 명시적으로 기록** 했기 때문이다.
검증 파일의 ParentId 는 일반적 계층 추적 용도가 아님.

대체 소스 조사:
- **`AllProperties.csv` ParentId 컬럼**: 12,009 / 12,009 전부 채워져 있음 ✓
- Level 분포도 완벽하게 일치함 (0: 1, 1: 4, 2: 144, 3: 34, 4: 116, 5: 640, 6: 3320, 7: 4460, 8: 2968, 9: 322)
- 루트 (Level 0) 의 ParentId 는 sentinel `00000000-0000-0000-0000-000000000000` (빈 GUID)

**결론**: `AllProperties.csv` 가 유일한 신뢰할 수 있는 ParentId 소스이다.

---

## 4. 해결방안

### 수정 1: `clean.py` 에 `load_hierarchy_from_all_properties()` 추가

```python
def load_hierarchy_from_all_properties(path=None) -> pd.DataFrame:
    df = pd.read_csv(
        path or config.RAW_ALL_PROPERTIES,
        usecols=["ObjectId", "ParentId", "Level"],
        low_memory=False,
    )
    df = df.rename(columns={"ObjectId":"object_id", "ParentId":"parent_id", "Level":"level"})
    df["parent_id"] = df["parent_id"].where(df["parent_id"] != EMPTY_GUID, None)
    df["level"] = pd.to_numeric(df["level"], errors="coerce").astype("Int64")
    return df
```

### 수정 2: `VALIDATION_DROP_COLS` 에 `ParentId` 추가

```python
VALIDATION_DROP_COLS = ("DisplayName", "ParentId")
```

validation.csv 의 parent_id 는 불완전하므로 join 대상에서 제외.

### 수정 3: `build_bim_hierarchy_silver()` 를 AllProperties 기반으로 전환

```python
def build_bim_hierarchy_silver(all_properties_path=None):
    return load_hierarchy_from_all_properties(all_properties_path)
```

### 수정 4: `build_bim_objects_gold()` 에 AllProperties 조인 단계 추가

```python
merged = silver.merge(hierarchy[["object_id","parent_id"]], on="object_id", ...)
merged = merged.merge(val, on="object_id", ...)
```

### 수정 5: `EMPTY_GUID` 상수 선언

```python
EMPTY_GUID = "00000000-0000-0000-0000-000000000000"
```

루트의 sentinel 을 None 으로 변환하여 `parent_id IS NULL` 쿼리가 제대로 동작하도록.

---

## 5. 결과

✅ **pytest 149/149 전체 통과** (49.28초)
```
tests/test_config.py                          3 passed
tests/test_ingest/test_unit_parser.py        44 passed
tests/test_ingest/test_xlsx_classifier.py    29 passed  (oracle 100%)
tests/test_ingest/test_xlsx_loader.py        30 passed
tests/test_ingest/test_clean.py              32 passed
tests/test_ingest/test_sqlite_writer.py      11 passed
```

✅ **Phase 1a 파이프라인 산출물 검증**:
```
silver_objects_rows          : 12,009
silver_adjacency_rows        : 110,173
silver_hierarchy_rows        : 12,009
silver_connected_groups_rows : 3,355
gold_objects_rows            : 12,009
gold_objects_columns         : 216
gold_adjacency_sym_rows      : 220,346
```

✅ **데이터 품질 검증**:
```
Flag 분포:
  is_container           : 3,353  (= giant group complement, 정확)
  is_bbox_placeholder    :   671
  is_analysis_volume     :   145  (Insulation Volume 전량)
  has_own_geometry       : 7,985
  graph_participant      : 7,840

SI unit 파싱 성공률:
  dry_weight_kg          : 5,135
  length_m               : 1,690
  design_pressure_kpa    : 2,356
  design_temperature_c   : 2,356
  npd_end1_m             : 2,926

Join 무결성 (모두 12,009/12,009):
  parent_id (루트 제외)   : 12,008 ✓
  mesh_quality           : 12,009 ✓
  centroid_x/y/z         : 12,009 ✓
  group_id               : 12,009 ✓

Title fallback: 0 건 발생 (모든 display_name 이 비어있지 않음)

Lineage (모든 행 동일):
  refining_rule          : 'xlsx_refined_exporter'
  refining_rule_version  : 'DXTnavis@main (snapshot 20260407-192047)'
  ingested_at_utc        : ISO 8601 UTC timestamp
```

✅ **클래스 분포 (XLSX 원본 그대로 유지)**:
```
Structure     5,926
Piping        4,014
Equipment       851
Other           697
Electrical      449
HVAC             72
Total        12,009
```

✅ **파일 출력 확인**:
- `data/clean/2026-04-07/*.parquet` (4 파일)
- `data/enriched/2026-04-07/*.parquet` (2 파일)
- `data/enriched/2026-04-07/bimkg.db` (SQLite)

### 다음 단계

Phase 1a 완료. Phase 1c (SQLite 스키마 확장) 는 `run_phase_1a()` 가 이미 수행하므로
별도 작업 불필요 → Task #4 (`Phase 1c: SQLite schema enrichment`) 를 `completed` 로 마킹.

**다음 작업**:
- **Phase 1d**: PowerBI CSV 재생성 (`data/powerbi/2026-04-07/`) — bim_objects_enriched 에서 star schema 출력
- **Phase 1d 확장**: Foundry-ready Parquet 를 Object Type 별로 분할 (`data/ontology/2026-04-07/object_types/`)
- **Phase 2**: OWL 온톨로지 + RDF 인스턴스 생성
