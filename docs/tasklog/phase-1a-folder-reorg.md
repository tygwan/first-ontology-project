# Phase 1a — Folder Reorganization (Step 3.5)

**일자**: 2026-04-11
**담당 Task**: #2 (Phase 1a 준비 작업)
**커밋**: (pending)

---

## 1. 언어 / 내용

| 언어 | 변경 대상 | 목적 |
|------|---------|------|
| Shell | 디렉터리 구조 | Medallion architecture (Bronze/Silver/Gold/Ontology) 적용 |
| Shell | 파일 이동 | legacy 보존 + docs 정리 |
| Python | `src/bimkg/config.py` | 새 경로 상수 추가, SQLITE_DB → LEGACY_SQLITE alias |
| Markdown | `README.md` | 전면 재작성 (expandable 섹션 6개) |
| Markdown | `docs/README.md` | 신규 — docs 인덱스 작성 |

**변경된 디렉터리 구조**:

```
data/
├── raw/         (Bronze, UNCHANGED)
├── clean/       (Silver, NEW)
├── enriched/    (Gold, NEW)
├── ontology/    (Foundry Object/Link Types, NEW)
│   └── 2026-04-07/
│       ├── object_types/
│       ├── link_types/
│       └── owl/
└── backup/      (NEW)
    └── dxtnavis-csharp-20260411/
        ├── working/  (moved from data/working/)
        └── powerbi/  (moved from data/powerbi/)

docs/
├── README.md    (NEW)
├── reference/   (NEW - 4 legacy docs moved)
├── analysis/    (UNCHANGED)
├── plan/        (UNCHANGED)
└── tasklog/     (UNCHANGED)
```

**Foundry 친화성**:
- Palantir Foundry 의 표준 패턴인 Bronze/Silver/Gold/Ontology 4계층 반영
- 스냅샷 날짜 기준 (`2026-04-07`) 디렉터리 — Foundry 의 dataset versioning 과 유사
- Object Type / Link Type 분리 — Foundry 의 Ontology 등록 구조와 직접 매핑
- 모든 산출물 Parquet 형식 (Foundry 내부 포맷과 일치)

---

## 2. 문제

**문제 없음**. 디렉터리 생성 → 파일 이동 → config 업데이트 → 테스트 재실행 순서로 진행했으며,
각 단계마다 `pytest` 실행으로 regression 없음을 확인.

단, 진행 중에 인지한 **작은 리스크**: `conftest.py` 의 `sqlite_ro` fixture 가 `config.SQLITE_DB` 를 참조하는데,
이 상수의 경로가 `data/working/dxtnavis/dxtnavis-semantic.db` 에서 `data/backup/dxtnavis-csharp-20260411/working/dxtnavis/dxtnavis-semantic.db` 로 변경되었다.
fixture 는 파일 부재 시 `pytest.skip()` 으로 처리하도록 되어있어 **현재는 어느 테스트도 sqlite_ro 를 사용하지 않기 때문에 영향 없음**.

---

## 3. 분석

### Foundry Medallion Architecture 선택 이유

| 대안 | 장단점 |
|------|-------|
| **(a) 단순 `data/processed/`** | 장: 직관적. 단: Silver/Gold 구분 없음, Foundry 매핑 시 재구성 필요 |
| **(b) Phase 별 `phase1/`, `phase2/`** | 장: 코드와 1:1. 단: 데이터 관점에서는 부자연스러움, 재사용 어려움 |
| **(c) Medallion (Bronze/Silver/Gold/Ontology)** ★ 선택 | 장: Foundry 표준, 각 계층의 책임 명확, 다중 스냅샷 지원. 단: 약간의 학습 곡선 |

Palantir Foundry Developer Tier 에 직접 import 하는 것이 목표이므로,
Foundry 의 기본 파이프라인 패턴과 동일한 구조를 유지하면 migration 비용이 0 에 가깝다.

### legacy 삭제 vs 백업 결정

사용자 지시대로 **백업** 선택. 이유:

1. `dxt_schedule_tasks` 9개 run (3,556 tasks) 는 Phase 4/5 에서 비교 벤치마크로 쓸 수 있음
2. `synth_timeliner.csv` 6,721 tasks 는 합성 스케줄 예시로 참고 가능
3. 삭제는 일방향, 백업은 필요 시 복원 가능
4. 1.7GB 가 큰 것처럼 느껴지지만 디스크 공간은 거의 무료

### `SQLITE_DB` 상수 처리

`conftest.py` 와 미래 코드의 하위 호환성을 위해 상수를 삭제하지 않고 `LEGACY_SQLITE` 로 alias.
```python
# Deprecated alias -- kept for backward compatibility
SQLITE_DB: Path = LEGACY_SQLITE
```
새 코드는 명시적으로 `SQLITE_BIMKG` (enriched/bimkg.db) 또는 `LEGACY_SQLITE` 를 사용해야 한다.

---

## 4. 해결방안

### Phase A — 디렉터리 생성

```bash
mkdir -p data/clean/2026-04-07
mkdir -p data/enriched/2026-04-07
mkdir -p data/ontology/2026-04-07/{object_types,link_types,owl}
mkdir -p data/backup/dxtnavis-csharp-20260411/{working,powerbi}
mkdir -p docs/reference
```

### Phase B — 파일 이동

```bash
# docs 정리 (git mv - 이력 추적 보존)
git mv docs/DATA-SPECIFICATION.md docs/reference/
git mv docs/dxtnavis-2026-04-07-*.md docs/reference/

# data/working/ → data/backup/ (디렉터리 전체)
mv data/working data/backup/dxtnavis-csharp-20260411/working-staged
mv data/backup/dxtnavis-csharp-20260411/working-staged/* \
   data/backup/dxtnavis-csharp-20260411/working/
rmdir data/backup/dxtnavis-csharp-20260411/working-staged

# data/powerbi/ → data/backup/
mv data/powerbi/2026-04-07 data/backup/dxtnavis-csharp-20260411/powerbi/2026-04-07
rmdir data/powerbi
```

### Phase C — README 재작성

- `README.md` 전면 재작성 (6개 `<details>` expandable 섹션)
  - Project Structure
  - Pipeline Architecture
  - Data Flow (Medallion)
  - Development Commands
  - Current Status
  - Palantir Foundry Integration
  - Repository Conventions
- `docs/README.md` 신규 작성 (docs 인덱스)

### Phase D — config.py 업데이트

Medallion 계층별 경로 상수 추가:
- `DATA_CLEAN_ROOT`, `DATA_CLEAN`
- `DATA_ENRICHED_ROOT`, `DATA_ENRICHED`
- `DATA_ONTOLOGY_ROOT`, `DATA_ONTOLOGY`
- `DATA_BACKUP_ROOT`
- `ONTOLOGY_OBJECT_TYPES`, `ONTOLOGY_LINK_TYPES`, `ONTOLOGY_OWL_DIR`
- `CLEAN_OBJECTS`, `CLEAN_ADJACENCY`, `CLEAN_HIERARCHY`, `CLEAN_CONNECTED_GROUPS`
- `ENRICHED_OBJECTS`, `ENRICHED_ADJACENCY_SYM`
- `SQLITE_BIMKG` (enriched/bimkg.db 로 이동)
- `LEGACY_SQLITE`, `LEGACY_POWERBI`, `BACKUP_CSHARP`
- `RAW_REFINING_XLSX` (신규 — XLSX 를 primary source 로 참조)

### Phase E — 커밋

단일 커밋으로 모든 변경 반영:
- docs 파일 4개 renamed
- README.md 전면 재작성
- docs/README.md 신규
- src/bimkg/config.py 업데이트
- docs/tasklog/phase-1a-folder-reorg.md 신규 (이 문서)

---

## 5. 결과

✅ **pytest 76/76 통과** (10.67초)
- Phase D 후 config 변경 검증
- Phase E 전 최종 검증 — 회귀 0건

✅ **디렉터리 구조 확인**:
```
data/
├── backup/dxtnavis-csharp-20260411/
│   ├── powerbi/2026-04-07/     (13 files, 36MB)
│   └── working/                (1.7GB legacy)
├── clean/2026-04-07/           (empty, Phase 1a 대기)
├── enriched/2026-04-07/        (empty, Phase 1a 대기)
├── ontology/2026-04-07/
│   ├── link_types/
│   ├── object_types/
│   └── owl/
└── raw/dxtnavis/2026-04-07/    (UNCHANGED, 100MB)
```

✅ **legacy 보존 확인**:
- `data/backup/dxtnavis-csharp-20260411/working/dxtnavis/dxtnavis-semantic.db` (259MB SQLite)
- `data/backup/dxtnavis-csharp-20260411/working/dxtnavis/neo4j/` (5 batches)
- `data/backup/dxtnavis-csharp-20260411/working/dxtnavis/refining/` (5 runs)
- `data/backup/dxtnavis-csharp-20260411/working/dxtnavis/schedule/` (9 runs)
- `data/backup/dxtnavis-csharp-20260411/working/dxtnavis/timeliner/`
- `data/backup/dxtnavis-csharp-20260411/working/harness/`

✅ **git mv 를 통한 이력 보존**: 4개 reference 문서의 git history 가 이동 후에도 유지됨

### 다음 단계

폴더 구조가 확정되었으므로 **Phase 1a Step 4 (xlsx_loader + clean + sqlite_writer) 구현** 준비 완료.

새 구현 파일은 아래 경로로 간다:
- `src/bimkg/ingest/xlsx_loader.py`
- `src/bimkg/ingest/clean.py`
- `src/bimkg/ingest/sqlite_writer.py`
- 테스트: `tests/test_ingest/test_xlsx_loader.py`, `test_clean.py`, `test_sqlite_writer.py`

출력 대상:
- `data/clean/2026-04-07/bim_objects.parquet` (Silver)
- `data/clean/2026-04-07/bim_adjacency.parquet` (Silver)
- `data/clean/2026-04-07/bim_hierarchy.parquet` (Silver)
- `data/clean/2026-04-07/bim_connected_groups.parquet` (Silver)
- `data/enriched/2026-04-07/bim_objects_enriched.parquet` (Gold)
- `data/enriched/2026-04-07/bim_adjacency_sym.parquet` (Gold)
- `data/enriched/2026-04-07/bimkg.db` (Gold, SQLite canonical)
