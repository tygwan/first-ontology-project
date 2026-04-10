# Phase 1d — Power BI + Foundry Exports

**일자**: 2026-04-11
**담당 Task**: #12
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 파일 | 목적 |
|------|------|------|
| Python | `src/bimkg/ingest/exporters/__init__.py` | 서브패키지 초기화 + 모듈 설명 |
| Python | `src/bimkg/ingest/exporters/powerbi.py` | 10 CSV + README.md 생성, `run_powerbi_export()` 엔트리 |
| Python | `src/bimkg/ingest/exporters/foundry.py` | 6 Object Type + 4 Link Type Parquet 생성, `run_foundry_export()` 엔트리 |
| Python | `tests/test_ingest/test_exporters/__init__.py` | 빈 파일 (패키지 마커) |
| Python | `tests/test_ingest/test_exporters/test_powerbi.py` | 22 테스트 — row count, 파일 존재, FK 무결성, 컬럼 schema |
| Python | `tests/test_ingest/test_exporters/test_foundry.py` | 21 테스트 — Object Type 분할, Link Type schema, cross-reference 무결성 |

### Power BI 산출물 (10 파일 + README)

모두 `data/powerbi/2026-04-07/` 에 쓰여짐:

| 파일 | 행수 | 설명 |
|------|------|------|
| `fact_objects.csv` | 12,009 | 65 컬럼 (64 curated + 1 derived `in_giant_group`) |
| `fact_adjacency.csv` | 110,173 | 방향 있는 edges + `edge_id` |
| `fact_adjacency_undirected.csv` | 110,173 | pair-dedupe 된 edges + `pair_id` + lex 정렬 endpoints |
| `bridge_group_member.csv` | 12,009 | `object_id ↔ group_id` |
| `dim_class.csv` | 6 | XLSX 6 클래스 + order + color + percentage |
| `dim_level.csv` | 10 | Level 0-9 |
| `dim_pipeline.csv` | 147 | pipeline_name + object_count + pipe_run_count + primary/all npds + specs |
| `dim_meshq.csv` | 4 | mesh_quality + is_container flag |
| `dim_verdict.csv` | 4 | verdict + is_ok flag |
| `dim_group.csv` | 3,355 | 연결 그룹 메타 + is_giant + is_singleton |

제거된 legacy 파일: `fact_schedule_links.csv`, `dim_task.csv` (스케줄 데이터 없음).
추가 예정 연기: `dim_material.csv`, `dim_spec.csv` → Phase 2 에서 OWL Material/Specification 클래스로 통합.

### Foundry 산출물 (6 Object Types + 4 Link Types)

모두 `data/ontology/2026-04-07/` 에 쓰여짐:

**Object Types (`object_types/`, 216 컬럼 all-in-one)**:
| 파일 | 행수 | Foundry Object Type |
|------|------|-------------------|
| `piping.parquet` | 4,014 | PipingComponent |
| `structural.parquet` | 5,926 | StructuralMember |
| `equipment.parquet` | 851 | Equipment |
| `electrical.parquet` | 449 | ElectricalComponent |
| `hvac.parquet` | 72 | HvacComponent |
| `other.parquet` | 697 | OtherObject |

**Link Types (`link_types/`)**:
| 파일 | 행수 | 설명 |
|------|------|------|
| `adjacent_to.parquet` | 110,173 | Producer adjacency + `is_symmetric=True` 플래그 (양방향 저장 안 함) |
| `has_parent.parquet` | 12,008 | `child_object_id`, `parent_object_id`, `child_level` (루트 제외) |
| `belongs_to_pipeline.parquet` | 2,926 | Piping 객체 중 pipeline 비어있지 않은 건 |
| `in_group.parquet` | 12,009 | `object_id`, `group_id`, `is_giant_group` |

---

## 2. 문제

**문제 #1**: `test_fact_objects_has_65_plus_1_columns` 실패
```
AssertionError: assert 65 == 66
```
테스트에서 `len(df.columns) == 66` 를 기대했으나 실제는 65 컬럼.

---

## 3. 분석

Plan 단계에서 계산한 "65 curated columns" 가 실제 `FACT_OBJECTS_COLUMNS` 에 정의한 수와 일치하지 않음.

각 카테고리별로 재확인:
```
식별    : 6 (object_id, title, display_name, parent_id, level, system_path)
분류    : 5 (class_raw, refined_class, original_class, nav_class_display_name, nav_item_type)
배관    : 6 (sp3d_pipeline ... sp3d_flow_direction)
장비    : 5 (sp3d_equipment_name, eqp_type_0~3)
자재    : 4 (material, material_grade, material_name, material_type)
시공    : 3 (construction_type, status, location)
기하    : 9 (centroid xyz, bbox min xyz, bbox max xyz)
메시    : 5 (mesh_quality, verdict, has_real_mesh, vertex_count, triangle_count)
SI단위  : 9 (dry_weight_kg, wet_weight_kg, length/width/depth/height removed → length/width/depth + pressure/temp + npd_end1/2)
플래그  : 5 (container, bbox_placeholder, analysis_volume, own_geometry, graph_participant)
그룹    : 2 (group_id, group_size — in_giant_group 은 파생이므로 목록 제외)
lineage : 5 (refining_rule, rule_version, ingested_at_utc, adjacency_count, child_count)

합계: 6+5+6+5+4+3+9+5+9+5+2+5 = 64
```

**64 curated + 1 derived (in_giant_group) = 65 총 컬럼**.

Plan 단계에서 "그룹 - 3" 이라고 세면서 `in_giant_group` 를 목록에 넣은 듯 착각했음. 파생 컬럼이므로 목록에는 64 만 있어야 함.

---

## 4. 해결방안

테스트 이름과 assertion 수정:
```python
def test_fact_objects_has_64_plus_1_columns(powerbi_summary) -> None:
    df = pd.read_csv(config.POWERBI_DIR / "fact_objects.csv", nrows=1)
    assert len(FACT_OBJECTS_COLUMNS) == 64
    assert len(df.columns) == 65
```

`FACT_OBJECTS_COLUMNS` 상수 자체의 값은 올바르므로 수정 불필요.

---

## 5. 결과

✅ **pytest 192/192 전체 통과** (55.50초)
```
tests/test_config.py                              3 passed
tests/test_ingest/test_unit_parser.py            44 passed
tests/test_ingest/test_xlsx_classifier.py        29 passed
tests/test_ingest/test_xlsx_loader.py            30 passed
tests/test_ingest/test_clean.py                  32 passed
tests/test_ingest/test_sqlite_writer.py          11 passed
tests/test_ingest/test_exporters/test_powerbi.py  22 passed
tests/test_ingest/test_exporters/test_foundry.py  21 passed
```

Phase 1d 만 +43 새 테스트.

✅ **Power BI 산출물 검증**:
- fact_objects: 12,009 × 65 컬럼
- 6 클래스 분포 (Structure 5,926 / Piping 4,014 / Equipment 851 / Other 697 / Electrical 449 / HVAC 72)
- FK 무결성: fact_objects ↔ dim_group, fact_adjacency ↔ fact_objects 전부 유효
- undirected adjacency 정렬 무결성: `object_a <= object_b` 전체 적용
- `in_giant_group` True 카운트 = 8,626 (EXPECTED_GIANT_GROUP_SIZE)
- UTF-8 BOM 인코딩으로 한글 유지

✅ **Foundry 산출물 검증**:
- 6 Object Type 합계 = 12,009 (정확히 원본 객체 수)
- Object Type 간 `object_id` 중복 없음 (각 객체는 정확히 하나의 Object Type 에 속함)
- 모든 Object Type parquet 이 216 컬럼 전체 보존 (all-in-one)
- Link Type endpoint 무결성: `adjacent_to`, `has_parent` 의 endpoint 가 모두 Object Type 안에 존재
- `adjacent_to.is_symmetric` 모두 True
- `has_parent` 12,008 건 (루트 제외)
- `belongs_to_pipeline` 2,926 건 (piping + pipeline non-null)
- `in_group.is_giant_group` True 카운트 = 8,626

✅ **파일 크기 검증** (`du -h`):
```
data/powerbi/2026-04-07/         ~35 MB (legacy 와 유사)
data/ontology/2026-04-07/
  object_types/                  ~50 MB (216 컬럼 × 12,009 rows 분할)
  link_types/                    ~18 MB
```

### Phase 1 전체 완료 체크리스트

| 서브페이즈 | 상태 | 산출물 |
|----------|------|-------|
| Phase 1a | ✅ | `bim_objects_enriched.parquet`, `bimkg.db`, Silver/Gold 계층 |
| Phase 1b | ✅ | `unit_parser.py`, 44 단위 테스트 |
| Phase 1c | ✅ | SQLite canonical store (Phase 1a 에 통합) |
| Phase 1d | ✅ | 10 PowerBI CSV + 10 Foundry Parquet + README |

### 다음 단계

**Phase 2: OWL 온톨로지 + RDF 인스턴스** 가 다음입니다:
- `data/ontology/2026-04-07/object_types/*.parquet` 를 OWL TBox 로 변환
- RDF 인스턴스 생성 (ABox)
- 이미 존재하는 `spatial_relationships.ttl` (원본) 과 병합
- Foundry Ontology 에 import 하기 전에 로컬 SPARQL 검증

Phase 2 는 Phase 1d 의 Foundry-ready 파일을 입력으로 쓰므로 이미 준비 완료.
