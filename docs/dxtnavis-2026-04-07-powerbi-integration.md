# DXTnavis 2026-04-07 Power BI 연동 검토 및 가이드

**대상 데이터셋**: 2026-04-07 베이스라인 export (12,009 객체)
**번들 위치**: `data/powerbi/2026-04-07/` (UTF-8 BOM, star schema)
**번들 빌더**: `scripts/analysis/260407/build_powerbi_bundle.py`
**전제 인벤토리**: `scripts/analysis/260407/powerbi_inventory.py`

---

## 1. 결론 (한 줄)

**Yes, with two prep transforms.** 16개 후보 파일 중 14개는 그대로 Power BI 가져오기 가능, 1개는 컬럼명 정리 권장(`AllProperties_*.csv`, 한글 헤더 136개), 1개는 행 폭발 변환 필요(`connected_groups.csv`, MemberObjectIds 셀이 최대 319,161자). 그래서 Power BI에 직접 raw 파일을 로드하기보다 **`data/powerbi/2026-04-07/` 아래에 미리 정규화한 star schema 번들을 가져오는 것**이 가장 깔끔합니다.

---

## 2. 검토한 raw / working 파일들

| 파일 | 행 수 | 컬럼 | 인코딩 | Power BI 평가 |
|---|---:|---:|---|---|
| `raw/.../AllProperties_2026...csv` | 12,009 | 136 | utf-8-sig | ok but rename-recommended (한글 헤더) |
| `raw/.../geometry.csv` | 12,009 | 22 | utf-8-sig | ok |
| `raw/.../validation.csv` | 12,009 | 22 | utf-8-sig | ok |
| `raw/.../adjacency.csv` | 110,173 | 9 | utf-8-sig | ok |
| `raw/.../connected_groups.csv` | 3,355 | 16 | utf-8-sig | **needs-transform** (MemberObjectIds 폭발 필요) |
| `raw/.../tessellation_failures.csv` | 0 | 5 | utf-8-sig | ok (빈 파일) |
| `working/.../refining_all_objects.csv` | 12,009 | 14 | utf-8-sig | ok |
| `working/.../class_distribution.csv` | 5 | 2 | utf-8-sig | ok |
| `working/.../schedule_all_classes.csv` | 5 | 8 | utf-8-sig | ok |
| `working/.../task_object_links.csv` | 12,009 | 6 | utf-8-sig | ok |
| `working/.../neo4j_object_nodes.csv` | 12,009 | 14 | utf-8-sig | ok |
| `working/.../neo4j_property_nodes.csv` | 459,757 | 4 | utf-8-sig | ok (대용량) |
| `working/.../neo4j_class_nodes.csv` | 5 | 2 | utf-8-sig | ok |
| `working/.../neo4j_context_nodes.csv` | 3,874 | 6 | utf-8-sig | ok |
| `working/.../neo4j_task_nodes.csv` | 5 | 5 | utf-8-sig | ok |
| `working/.../neo4j_edges.csv` | 787,679 | 5 | utf-8-sig | ok (대용량, ETL 권장) |
| `working/.../dxtnavis-semantic.db` (SQLite) | — | — | — | ok via ODBC, 다만 CSV 번들이 더 단순 |

**주요 걸림돌**:
1. `connected_groups.csv`의 `MemberObjectIds`는 세미콜론 구분 리스트로, 가장 큰 그룹(8,626 객체)에서 셀 길이가 319,161자. Power Query가 한 셀에 통째로 들고 가긴 하지만 값으로 join이 안 됩니다 → 번들 빌더가 이걸 `bridge_group_member.csv` (12,009행 GroupId↔ObjectId)로 사전 폭발.
2. `AllProperties_*.csv`는 136개 중 다수가 한글 헤더(`객체이름`, `재질`, `공정`, ...). Power BI는 한글 헤더 자체는 처리하지만 측정값/관계 작성 시 가독성이 떨어짐 → 번들에서 영문 정규화된 컬럼만 노출.

---

## 3. Power BI 번들 (star schema)

**경로**: `data/powerbi/2026-04-07/`

```
fact_objects.csv             12,009 rows  ~5,967 KB   per-object 메인 fact
fact_adjacency.csv          110,173 rows ~15,579 KB   producer 인접 (방향 있음)
fact_adjacency_undirected   110,173 rows ~11,992 KB   동일 데이터, 무방향 1-row-per-pair
fact_schedule_links.csv      12,009 rows  ~1,485 KB   object → task (latest run)
bridge_group_member.csv      12,009 rows    ~507 KB   object ↔ connected group
dim_class.csv                     5 rows
dim_meshq.csv                     5 rows
dim_level.csv                    10 rows
dim_pipeline.csv                157 rows
dim_task.csv                      5 rows
dim_group.csv                 3,355 rows    ~378 KB
dim_verdict.csv                   5 rows
```

총 ~36 MB. 모든 파일 UTF-8 BOM이라 Power BI가 한글 자동 인식. fact_objects는 raw refining + geometry + validation을 ObjectId 기준으로 미리 join해 한 행에 정리했고, derived 필드 4개를 추가했습니다:

- `VolumeBucket`: zero / <1e-3 / 1e-3..0.1 / 0.1..1 / 1..10 / 10..100 / >=100
- `SizeBucket`: <0.1m / 0.1-0.5m / 0.5-2m / 2-5m / 5-20m / 20-100m / >=100m
- `DiagonalM`: bbox 대각선 길이(m)
- `InGiantGroup`: 연결 그룹 중 8,626 객체짜리 거대 그룹 소속 여부

---

## 4. 모델 다이어그램

```
                          ┌──────────────┐
                          │   dim_class  │
                          └──────┬───────┘
                                 │ Class
              ┌──────────────┐   │
              │  dim_pipeline├───┤ Pipeline
              └──────────────┘   │
              ┌──────────────┐   │
              │  dim_level   ├───┤ Level
              └──────────────┘   │
              ┌──────────────┐   │
              │  dim_meshq   ├───┤ MeshQuality
              └──────────────┘   │
              ┌──────────────┐   │
              │  dim_verdict ├───┤ Verdict
              └──────────────┘   │
                                 ▼
           ┌──────────────────────────────────┐
  ┌───────►│         fact_objects             │◄──────────┐
  │ ObjectId│  (12009 rows, 38 cols, PK ObjectId) │ ObjectId │
  │        └──────────────────────────────────┘           │
  │                  │ GroupId                            │
  │                  ▼                                    │
  │           ┌──────────────┐                            │
  │           │  dim_group   │                            │
  │           └──────┬───────┘                            │
  │                  │ GroupId                            │
  │                  ▼                                    │
  │           ┌─────────────────────┐                     │
  │           │ bridge_group_member │                     │
  │           └─────────────────────┘                     │
  │                                                       │
  │           ┌──────────────────────┐                    │
  └───────────┤ fact_schedule_links  ├────────────────────┘
              └──────────┬───────────┘
                         │ TaskId
                         ▼
                   ┌─────────┐
                   │ dim_task│
                   └─────────┘

           ┌──────────────────────────┐
   Source─►│ fact_adjacency           │◄─Target  (110173 rows)
           └──────────────────────────┘
   둘 다 fact_objects.ObjectId 와 many-to-one (cross-filter both)
```

---

## 5. Power BI에서 가져오기 (Get Data → Folder)

### 5-1. 폴더 한 번에 가져오기 (권장)

1. Get Data → Folder → `C:/Users/Yoon taegwan/Desktop/AWP_2025/개발폴더/ontology-for-cm/data/powerbi/2026-04-07`
2. **Combine** 누르지 말고 **Transform Data** 선택. 폴더 모드는 모든 CSV를 한 테이블로 합쳐버리니 안 됨.
3. Power Query에서 각 행(파일 한 개)을 **개별 쿼리로 분리**:
   - 우클릭 → Add as New Query → CSV.Document로 내용 펼치기
   - 또는 아래 `From Text/CSV`로 12개 파일 각각 임포트하는 게 더 명확

### 5-2. From Text/CSV 12번 (가장 직관적)

각 파일에 대해 Get Data → Text/CSV → 파일 선택. UTF-8 BOM 덕분에 인코딩 자동 감지. 첫 행이 헤더로 인식됨. 12번 반복.

### 5-3. Power Query M 스니펫 (가져오기 자동화용)

```powerquery
let
    Folder = "C:\Users\Yoon taegwan\Desktop\AWP_2025\개발폴더\ontology-for-cm\data\powerbi\2026-04-07",
    LoadCsv = (name as text) =>
        let
            Source = Csv.Document(
                File.Contents(Folder & "\" & name),
                [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
            Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
        in Promoted,

    fact_objects               = LoadCsv("fact_objects.csv"),
    fact_adjacency             = LoadCsv("fact_adjacency.csv"),
    fact_adjacency_undirected  = LoadCsv("fact_adjacency_undirected.csv"),
    fact_schedule_links        = LoadCsv("fact_schedule_links.csv"),
    bridge_group_member        = LoadCsv("bridge_group_member.csv"),
    dim_class                  = LoadCsv("dim_class.csv"),
    dim_meshq                  = LoadCsv("dim_meshq.csv"),
    dim_level                  = LoadCsv("dim_level.csv"),
    dim_pipeline               = LoadCsv("dim_pipeline.csv"),
    dim_task                   = LoadCsv("dim_task.csv"),
    dim_group                  = LoadCsv("dim_group.csv"),
    dim_verdict                = LoadCsv("dim_verdict.csv")
in
    fact_objects   // 첫 번째 쿼리만 반환, 나머지는 별도 쿼리로 만들어주세요
```

위는 자기 참조용 fragment입니다. 실제로는 12개 별도 쿼리로 만들어야 모델 뷰에 12개 테이블이 뜹니다.

---

## 6. 관계 설정 (Modeling → Manage Relationships)

| From | From column | To | To column | Cardinality | Cross filter |
|---|---|---|---|---|---|
| fact_objects | Class | dim_class | Class | Many → One | Single |
| fact_objects | MeshQuality | dim_meshq | MeshQuality | Many → One | Single |
| fact_objects | Level | dim_level | Level | Many → One | Single |
| fact_objects | Pipeline | dim_pipeline | Pipeline | Many → One | Single |
| fact_objects | Verdict | dim_verdict | Verdict | Many → One | Single |
| fact_objects | GroupId | dim_group | GroupId | Many → One | Single |
| fact_schedule_links | ObjectId | fact_objects | ObjectId | Many → One | Single |
| fact_schedule_links | TaskId | dim_task | TaskId | Many → One | Single |
| bridge_group_member | ObjectId | fact_objects | ObjectId | Many → One | Single |
| bridge_group_member | GroupId | dim_group | GroupId | Many → One | Single |
| fact_adjacency | SourceObjectId | fact_objects | ObjectId | Many → One | Both ⚠️ |
| fact_adjacency | TargetObjectId | fact_objects | ObjectId | Many → One | Single ⚠️ |

⚠️ **두 번째 관계는 Power BI가 "비활성"으로 강제합니다.** ObjectId → fact_objects 한 번에 두 가지 관계가 존재할 수 없기 때문입니다. 두 관계 다 활성화하려면:
- (a) `fact_adjacency`를 두 번 로드해서 한 번은 source용, 한 번은 target용으로 쓰거나
- (b) `dim_objects`를 별도 분리해 양쪽 모두 dim에 연결하는 패턴
- (c) DAX `USERELATIONSHIP()` 함수로 측정값에서 활성 관계 전환

가장 단순한 건 (a). 실제로 Power BI에서 같은 객체를 source 또는 target으로 보는 시각화가 동시에 필요하지 않으면 비활성 관계를 그냥 두어도 됩니다.

---

## 7. 추천 측정값 (DAX)

```dax
-- 전체 객체
Total Objects = COUNTROWS(fact_objects)

-- 컨테이너 제외 실제 객체
Real Objects = CALCULATE(
    COUNTROWS(fact_objects),
    fact_objects[Verdict] IN { "OK_MESH", "OK_FBX", "OK_LINE_MESH" }
)

-- 컨테이너 비율
Container Share % = DIVIDE(
    CALCULATE(COUNTROWS(fact_objects), fact_objects[Verdict] = "SKIP_CONTAINER"),
    COUNTROWS(fact_objects)
)

-- 평균 연결도 (producer adjacency)
Avg Producer Degree = AVERAGE(fact_objects[ProducerDegree])

-- 거대 그룹 점유율
In Giant Group % = DIVIDE(
    CALCULATE(COUNTROWS(fact_objects), fact_objects[InGiantGroup] = TRUE),
    COUNTROWS(fact_objects)
)

-- 메시 충실도
Full Mesh % = DIVIDE(
    CALCULATE(COUNTROWS(fact_objects), fact_objects[MeshQuality] = "full_mesh"),
    COUNTROWS(fact_objects)
)
```

---

## 8. 추천 페이지 구성

### 페이지 1 — Overview
- **카드**: Total Objects, Real Objects, Container Share %, Full Mesh %, Pipelines (`DISTINCTCOUNT(fact_objects[Pipeline])`)
- **도넛**: dim_class.Class × Total Objects (색상은 dim_class.ColorHex 직접 사용)
- **가로 막대**: dim_meshq × Total Objects (정렬은 MeshQualityOrder)
- **슬라이서**: dim_class, dim_level, dim_verdict

### 페이지 2 — Spatial / Quality
- **누적 막대**: dim_level × dim_class (heatmap 대용)
- **산점도**: fact_objects의 CentroidX × CentroidY, 색상=Class, 크기=DiagonalM
- **테이블**: SizeBucket × VolumeBucket × ObjectCount
- **슬라이서**: dim_class, dim_meshq, InGiantGroup

### 페이지 3 — Network / Adjacency
- **막대**: 상위 25 hubs (fact_objects ProducerDegree DESC + DisplayName)
- **테이블**: fact_adjacency_undirected의 RelationType × COUNT
- **카드**: 110,173 edges, average degree, max degree
- **슬라이서**: RelationType (overlap / touch / neartouch)

### 페이지 4 — Pipelines
- **막대**: 상위 20 dim_pipeline (PipeObjectCount DESC)
- **slicer를 통해 selected pipeline의 fact_objects 산점도**

### 페이지 5 — Schedule (현재는 5개 클래스 partition만 있음)
- **막대**: dim_task × ObjectCount
- 주의: 현재 schedule은 클래스 grouping이라 5개 task밖에 없음. Pipeline grouping으로 재실행하면 훨씬 더 의미있어짐 (project memory의 plan #4 참고)

---

## 9. 한계 (Power BI에서는 못 하는 것)

| 항목 | 이유 | 대안 |
|---|---|---|
| 4D 시뮬레이션 시간축 | 현재 schedule_all_classes 데이터에 시작/종료 날짜가 없음 (5개 partition만) | Pipeline grouping으로 재생성 후 calendar dim 추가 |
| 3D 시각화 | Power BI는 native 3D viewer 없음 | Plotly 3D scatter custom visual 또는 별도 web dashboard 사용 |
| 그래프 traversal (BFS/path) | Power BI는 graph 처리 안 함 | Neo4j (이미 working dir에 export 있음) |
| 사용자 정의 구역 polygon 필터 | Power BI 지도 시각화로는 BIM 좌표계 표현이 어려움 | scatter chart로 우회, 또는 별도 GIS 도구 |
| 2종 이상 양방향 self-join | adjacency.source/target 두 관계 동시 활성 불가 | DAX USERELATIONSHIP 또는 fact 복제 |

---

## 10. 갱신 시 (다음 export)

다음 export 디렉터리(`data/raw/dxtnavis/<날짜>`)가 들어오면:

1. `POST /dxtnavis/bundle/import` 로 refining + schedule + neo4j 재생성
2. `python scripts/analysis/260407/build_powerbi_bundle.py` (날짜만 바꿔서 새 폴더로 복사하거나 인자화)
3. Power BI에서 Refresh → 모든 12개 쿼리 자동 갱신

연락 가능한 폴더 경로 한 곳만 바꾸면 데이터 모델은 그대로 재사용됩니다.

---

## 11. 한 줄 요약

**`data/powerbi/2026-04-07/` 의 12개 CSV를 Power BI Get Data → Text/CSV로 가져오면 즉시 star schema 모델이 완성됩니다.** Raw 파일을 직접 가져오지 마세요 — `connected_groups.MemberObjectIds` 폭발과 한글 헤더 두 가지를 번들 빌더가 이미 처리해 두었습니다.
