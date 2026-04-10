# Phase 1 검증 가이드

> **목적**: Phase 1 (0, 1a~1d) 완료 후 사용자가 결과를 직접 검증할 수 있도록
> 출력물, 자동 검증된 항목, 수동 확인 필요 항목을 한 곳에 정리합니다.
>
> **작성 시점**: 2026-04-11
> **Phase 1 최종 커밋**: `eb67b43`

---

## 1. 현재 상태 한눈에 보기

### 1.1 데이터 디렉터리

| 경로 | 크기 | 내용 |
|------|-----:|------|
| `data/raw/dxtnavis/2026-04-07/` | 100 MB | 원본 DXTnavis 9 파일 (읽기 전용) |
| `data/clean/2026-04-07/` | 4 MB | Silver: 4 Parquet (snake_case, 타입 정규화) |
| `data/enriched/2026-04-07/` | 66 MB | Gold: 2 Parquet + bimkg.db SQLite |
| `data/powerbi/2026-04-07/` | 39 MB | Power BI star schema (10 CSV + README) |
| `data/ontology/2026-04-07/` | 6 MB | Foundry-ready (6 Object Type + 4 Link Type parquet) |
| `data/backup/dxtnavis-csharp-20260411/` | 1.7 GB | 동결된 legacy C# 백엔드 산출물 |

### 1.2 테스트 커버리지

| 모듈 | 테스트 수 | 커버 영역 |
|------|---------:|---------|
| `test_config.py` | 3 | 경로 상수, expected counts |
| `test_unit_parser.py` | 44 | SI 단위 파서 (length, weight, pressure, temperature, NPD) |
| `test_xlsx_classifier.py` | 29 | **Oracle 100% 일치** (C# ↔ Python) |
| `test_xlsx_loader.py` | 30 | XLSX 로드 + snake_case 정규화 + 충돌 감지 |
| `test_clean.py` | 32 | Silver/Gold 빌더, 플래그, SI 단위, lineage |
| `test_sqlite_writer.py` | 11 | run_phase_1a, Parquet roundtrip |
| `test_powerbi.py` | 22 | Power BI 10 CSV, FK 무결성, 컬럼 스키마 |
| `test_foundry.py` | 21 | Foundry 10 Parquet, Object ID uniqueness, Link endpoint |
| **Total** | **192** | Phase 0~1d 완전 커버 |

---

## 2. 자동으로 이미 검증된 것 (테스트 통과)

아래 항목은 `pytest` 가 통과했으므로 **사람이 다시 확인할 필요 없음**:

### 2.1 Row count 무결성

- [x] 12,009 객체 (모든 테이블)
- [x] 110,173 producer adjacency edges
- [x] 3,355 connected groups (giant = 8,626)
- [x] 6 classes = Structure 5,926 / Piping 4,014 / Equipment 851 / Other 697 / Electrical 449 / HVAC 72
- [x] 147 distinct pipelines (piping 객체 중)
- [x] 12,008 parent_id (1 null = 루트)

### 2.2 Oracle 동등성 (C# vs Python)

- [x] `test_oracle_100_percent_agreement`: `RefinedXlsxExporter.InferClass` (C#) 과 우리 Python 포트가 12,009 객체 전부에서 동일한 Class 값 생성. 재분류 로직의 재현 가능성 확보.

### 2.3 스키마 / 타입

- [x] XLSX 135 컬럼 전부 snake_case 변환 (pipe, Korean 없음)
- [x] Level 컬럼 Int64 캐스팅
- [x] Gold 테이블 216 컬럼 (XLSX 135 + 조인 65 + 플래그 5 + SI 11 + lineage 5)
- [x] Power BI fact_objects 65 컬럼 (64 curated + 1 derived)
- [x] Foundry Object Type 6 파일 각각 216 컬럼 (all-in-one)

### 2.4 파생 컬럼

- [x] `is_container` = 3,353 (skipped_container ∩ adjacency=0)
- [x] `is_bbox_placeholder` = 671 (box_placeholder mesh quality)
- [x] `is_analysis_volume` = 145 (Insulation Volume 이름 패턴)
- [x] `has_own_geometry` = 7,985 (full_mesh + fbx_supplemented + 일부)
- [x] `graph_participant` = 7,840 (위 3개 제외)
- [x] `in_giant_group` = 8,626

### 2.5 SI 단위 파싱 커버리지 (원본 값 있는 행에서 100%)

- [x] `dry_weight_kg`: 5,135 rows, max 147,326.8 kg
- [x] `length_m`: 1,690 rows, max 56.55 m
- [x] `design_pressure_kpa`: 2,356 rows, max 1,206.6 kPa
- [x] `design_temperature_c`: 2,356 rows, max 260 ℃
- [x] `npd_end1_m`: 2,926 rows, min 0.013 m (½") max 0.610 m (24")

### 2.6 FK / Link 무결성

- [x] Power BI: bridge_group_member → dim_group, fact_objects → dim_group, fact_adjacency → fact_objects
- [x] Foundry: adjacent_to, has_parent endpoint 들이 모두 Object Type 파일 안에 존재
- [x] Foundry: 6 Object Type 간 object_id 중복 0건, 합계 = 12,009

---

## 3. 수동 검증이 필요한 것

아래 항목은 **엔지니어링 도메인 지식 또는 시각적 판단** 이 필요합니다.

### 3.1 클래스 분류의 도메인 정확성 ★ 최우선

**확인 방법**: Power BI 또는 파이썬에서 샘플 추출

```python
from bimkg import config
import pandas as pd
gold = pd.read_parquet(config.ENRICHED_OBJECTS)

# 각 클래스에서 랜덤 샘플 30개씩 뽑아 display_name 확인
for cls in ['Structure', 'Piping', 'Equipment', 'Electrical', 'HVAC', 'Other']:
    sample = gold[gold['refined_class'] == cls][['object_id','display_name','system_path','sp3d_eqp_type_0']].sample(30, random_state=42)
    print(f"\n=== {cls} ({len(gold[gold['refined_class']==cls])} total) ===")
    print(sample.to_string())
```

**체크 포인트**:
- [ ] Structure 샘플이 실제 구조물(Beam/Column/Slab/Footing)인가?
- [ ] Piping 샘플이 실제 배관 부품(Pipe/Valve/Flange/Tee)인가?
- [ ] Equipment 샘플이 실제 장비인가? `sp3d_eqp_type_0` 이 채워져 있는가?
- [ ] Electrical 449 건이 실제 전기 요소 (Cableway/Conduit) 인가?
- [ ] HVAC 72 건이 실제 공조 요소 (Duct) 인가?
- [ ] Other 697 건이 정말 분류 불가한 객체인가? (일부는 잠재적 Structural 일 수 있음)

**잘못된 분류 발견 시**: `docs/analysis/refined-xlsx-exporter-logic.md` 의 3-tier 로직과 키워드를 참조하여 패턴 확장 고려. 이것은 Phase 2 온톨로지 설계 전에 해결되어야 함.

### 3.2 Pipeline 분류 검증

**확인 방법**:
```python
piping = gold[gold['refined_class'] == 'Piping']
print(f"Piping with pipeline set: {piping['sp3d_pipeline'].notna().sum()}")
print(f"Piping without pipeline:  {piping['sp3d_pipeline'].isna().sum()}")

# 가장 큰 파이프라인 10개
top = piping['sp3d_pipeline'].value_counts().head(10)
print(top)
```

**체크 포인트**:
- [ ] 예상 파이프라인 이름이 나타나는가?
- [ ] "Pipelines" 라는 값이 153건 있는데 (Top 10) — 이게 실제 파이프라인 이름인지, 아니면 SP3D 메타 필드 오염인지 확인 필요
- [ ] Piping 클래스 4,014 개 중 1,088 개가 pipeline 속성이 비어있음 — 정상인지?

### 3.3 공간 분포 시각 검증 ★ Power BI 필수

**확인 방법**: Power BI 에서 `fact_objects.centroid_x`, `centroid_y` 로 2D 산점도 생성

**체크 포인트**:
- [ ] 객체들이 plant layout 처럼 보이는가? (벽, 바닥, 파이프가 이해되는 형태인가)
- [ ] 각 클래스를 색으로 구분했을 때 공간 집중이 자연스러운가?
- [ ] 이상치 (예: 플랜트 외부에 떠 있는 객체) 가 있는가?

### 3.4 고립 객체 검증

**확인 방법**:
```python
isolated = gold[gold['adjacency_count'] == 0]
print(f"Isolated objects: {len(isolated)}")
print(isolated['refined_class'].value_counts())
print(isolated['mesh_quality'].value_counts())
```

**체크 포인트**:
- [ ] 3,353 건 (singleton) 이 예상된 값인가
- [ ] Piping 153 건이 고립되어 있음 — 이들이 실제 "유실된" 배관인지 확인

### 3.5 Insulation Volume 등 분석 아티팩트

**확인 방법**:
```python
av = gold[gold['is_analysis_volume']]
print(f"Analysis volumes: {len(av)}")
print(av['refined_class'].value_counts())
print(av['display_name'].str.extract(r'^(\w+\s+\w+)')[0].value_counts())
```

**체크 포인트**:
- [ ] 145 건 모두 `Insulation Volume` 인가?
- [ ] 이들이 여러 클래스 (Piping/Equipment/HVAC) 에 걸쳐 있는 것이 타당한가?
- [ ] `Obstruction Volume`, `Fireproofing Volume` 은 0건인가?

---

## 4. Power BI Desktop import 가이드

### 4.1 준비

1. Windows 에서 Power BI Desktop 설치 (Microsoft Store 무료)
2. `data/powerbi/2026-04-07/` 디렉터리를 Windows 로 복사하거나 공유 경로 설정

### 4.2 Import 순서

1. **Power BI Desktop → Get Data → Text/CSV**
2. **10 파일 전부 import** (UTF-8 BOM 자동 인식)
3. **Modeling → Manage Relationships** 에서 star schema 구성:

```
dim_class[class_name]       ───► fact_objects[refined_class]
dim_level[level]            ───► fact_objects[level]
dim_meshq[mesh_quality]     ───► fact_objects[mesh_quality]
dim_verdict[verdict]        ───► fact_objects[verdict]
dim_pipeline[pipeline_name] ───► fact_objects[sp3d_pipeline]
dim_group[group_id]         ◄─── bridge_group_member[group_id]
                            ◄─── fact_objects[group_id]

fact_adjacency[source_object_id] ───► fact_objects[object_id]
fact_adjacency[target_object_id] ───► fact_objects[object_id] (inactive)
```

4. **시각화 페이지 3개 제안**:
   - **Overview**: 클래스별 카운트 카드, 클래스 분포 도넛, Level 히스토그램
   - **Spatial**: `centroid_x` × `centroid_y` 산점도 (색: refined_class, 크기: bbox_volume_m3)
   - **Quality**: `mesh_quality` × `verdict` 매트릭스, `is_container`/`is_analysis_volume` 파이

### 4.3 Sanity check 숫자

아래 값이 대시보드에서 확인되어야 함:

| 메트릭 | 기대값 |
|--------|-------|
| Total objects | **12,009** |
| Piping count | 4,014 (33.4%) |
| Structure count | 5,926 (49.3%) |
| Equipment count | 851 (7.1%) |
| Full mesh count | 7,189 |
| Skipped container count | 3,353 |
| Giant group size | 8,626 |
| Adjacency edges | 110,173 (fact_adjacency) |
| Pipelines | 147 distinct |

---

## 5. 빠른 파이썬 검증 스니펫

### 5.1 Gold 테이블 탐색

```python
import pandas as pd
from bimkg import config

gold = pd.read_parquet(config.ENRICHED_OBJECTS)

# 전체 개요
print(gold.shape)                           # (12009, 216)
print(gold.columns.tolist()[:20])           # 처음 20 컬럼

# 클래스별 중량 통계
print(gold.groupby('refined_class')['dry_weight_kg'].describe())

# Level 별 클래스 매트릭스
print(pd.crosstab(gold['level'], gold['refined_class']))
```

### 5.2 SQLite 쿼리

```bash
sqlite3 data/enriched/2026-04-07/bimkg.db
```
```sql
SELECT refined_class, COUNT(*) FROM bim_objects GROUP BY refined_class;

SELECT sp3d_pipeline, COUNT(*) AS n, AVG(dry_weight_kg) AS avg_kg
FROM bim_objects
WHERE refined_class = 'Piping' AND sp3d_pipeline IS NOT NULL
GROUP BY sp3d_pipeline
ORDER BY n DESC
LIMIT 20;

-- 가장 연결이 많은 객체 (adjacent_count 기준)
SELECT object_id, display_name, refined_class, adjacency_count
FROM bim_objects
ORDER BY adjacency_count DESC
LIMIT 10;
```

### 5.3 Foundry Parquet 탐색

```python
from bimkg import config
import pandas as pd

# 각 Object Type 파일 확인
for cls_file in (config.ONTOLOGY_OBJECT_TYPES).iterdir():
    df = pd.read_parquet(cls_file)
    print(f"{cls_file.name}: {df.shape}, unique={df['object_id'].nunique()}")

# Link Type 탐색
parent = pd.read_parquet(config.ONTOLOGY_LINK_TYPES / "has_parent.parquet")
print(parent.head())
```

---

## 6. 알려진 이슈 / 주의할 점

### 6.1 "Pipelines" 라는 sp3d_pipeline 값 153건

Top 10 pipeline list 에 `Pipelines` 라는 이름이 나타납니다. 이는 아마:
- SP3D 에서 원본 `Pipeline` 속성이 라벨 처리 오류로 "Pipelines" 문자열 값이 채워진 것
- 또는 Navisworks 에서 `Pipeline` 카테고리 이름을 속성값으로 잘못 매핑한 것

**영향**: `dim_pipeline.csv` 에 `Pipelines` 라는 fake pipeline 1개가 포함됨 (147 중 1개). 사용자가 필터링 시 유념해야 함.

**권장 처리**: Phase 2 온톨로지 설계 시 `Pipeline` Object Type 을 정의하면서 이 fake pipeline 을 제거하거나 `is_valid_pipeline` 플래그를 추가.

### 6.2 Equipment 의 Eqp Type 0 커버리지 153/851 (18%)

Equipment 클래스 851 개 중 `sp3d_eqp_type_0` 이 채워진 것은 **153 개뿐** 입니다.
나머지 698 개는 SP3D 의 Equipment taxonomy 가 할당되지 않은 상태.

**영향**: Phase 2 에서 Equipment 의 subclass (Process Equipment, Electrical Equipment 등) 를 만들 때 698개는 "Equipment > Unclassified" 로 남음.

### 6.3 Pipeline 147 vs 157 불일치

- 우리 `dim_pipeline.csv`: 147 건 (XLSX 기반)
- 이전 legacy C# PowerBI bundle (`data/backup/...`): 157 건 (SQLite 기반)
- 차이 10 건 = `U12-*-MZ-*-1S3984` 시리즈

**원인**: XLSX 의 `RefinedXlsxExporter.FindKey` 가 "Pipeline" 이름의 첫 번째 속성만 선택하는 버그. 다른 카테고리 (`Item|Pipeline` 등) 에 있는 pipeline 이름이 누락됨.

**영향**: XLSX 를 oracle 로 쓰기로 했으므로 147 을 기준으로 갑니다. Phase 2 에서 온톨로지를 만들 때 이 10 건을 AllProperties.csv 에서 복원할지 결정 필요.

### 6.4 wet_weight_kg 데이터 부족

116 건만 채워져 있음. 대부분 Equipment 에 해당하며, 유체를 담는 vessel/tank 만 이 속성이 있음.

**영향**: Phase 4 그래프 분석에서 wet weight 를 크리티컬 패스 추정에 쓰기 어려움.

### 6.5 Height 등 일부 SP3D 필드 매우 희소

- `sp3d_height` 45 건 (0.4%)
- `sp3d_diameter` 36 건 (0.3%)
- `sp3d_bend_radius` 42 건 (0.3%)

**영향**: 이 필드들은 Phase 2 온톨로지에서 optional property 로 모델링되어야 함.

---

## 7. 피드백 방식

수동 검증 중 이슈를 발견하면:

### Bug / data quality issue

```
Title: [Phase 1 Verify] 간결한 설명
Files: 어느 파일에서 발견했는지
Example: 구체 object_id 나 값
Expected vs Actual: 기대했던 것 vs 실제 본 것
Reproducibility: 재현 가능한 쿼리
```

### Enhancement / question

```
Title: [Phase 2 Prep] 간결한 설명
Context: 어느 Phase 에 영향
Proposal: 제안
```

이슈는 `docs/analysis/phase-1-verification-findings.md` 에 축적해서
Phase 2 시작 전에 일괄 반영할 수 있습니다.

---

## 8. 다음 단계

검증 완료 후:

| 결과 | 다음 단계 |
|------|----------|
| ✅ 문제 없음 | Phase 2 (OWL 온톨로지 + RDF 인스턴스) 바로 시작 |
| ⚠️ 경미한 이슈 (데이터 품질) | Phase 2 시작 전 Phase 1e 로 이슈 해결 |
| ❌ 중대한 이슈 (분류 오류 등) | Phase 1a 재검토 필요 |

**권장**: 3.1 (클래스 분류 도메인 정확성) 과 3.3 (공간 분포) 에 최소 1~2시간 투자하는 것을 강력 추천. 이 두 가지가 Phase 2 이후 모든 작업의 기반이 됩니다.
