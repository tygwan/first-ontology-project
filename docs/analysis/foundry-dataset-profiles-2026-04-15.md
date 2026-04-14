# Foundry Dataset Profiles — BIM-KG

**Generated**: 2026-04-15 (SDK auto-profile)
**SDK**: foundry-sdk v2 (`read_table`)
**Purpose**: Pre-computed context for AI FDE conversations
**Project**: `/Datayoon-09825c/BIM-KG`

Skim this first; saves AI FDE from recomputing basics.

## Summary

| Dataset | Type | Rows | Cols | Status |
|---|---|---:|---:|---|
| `bim_piping` | object | 3,062 | 219 | ✓ |
| `bim_structural` | object | 4,840 | 219 | ✓ |
| `bim_equipment` | object | 770 | 219 | ✓ |
| `bim_electrical` | object | 1,053 | 219 | ✓ |
| `bim_hvac` | object | 125 | 219 | ✓ |
| `bim_other` | object | 2,159 | 219 | ✓ |
| `bim_adjacent_to` | link | 110,173 | 7 | ✓ |
| `bim_has_parent` | link | 12,008 | 3 | ✓ |
| `bim_belongs_to_pipeline` | link | 2,926 | 3 | ✓ |
| `bim_in_group` | link | 12,009 | 3 | ✓ |


## Per-Dataset Profiles


### `bim_piping` (object)

- **Shape**: 3,062 rows × 219 cols
- **Column types**: 145 object, 41 float64, 21 bool, 12 int64
- **Completeness**: 200 cols ≥99% filled, 13 cols ≥50% null

**Key attributes**:
- `object_id` (0% null, 3,062 distinct): e.g., `0680b447-9986-5458-8148-323bb71cfddc`, `4d17925b-2739-5863-9348-53e70ba2f293`, `3fb29749-aa41-54d0-aead-8020ad9e1825`
- `display_name` (0% null, 1,810 distinct): e.g., `90 Degree Direction Change-1354`, `90 Degree Direction Change-1355`, `90 Degree Direction Change-1356`
- `refined_class` (0% null, 1 distinct): `Piping` (3,062, 100.0%)
- `sp3d_pipeline` (0% null, 148 distinct): e.g., `Pipelines`, `Pipelines`, `Pipelines`
- `sp3d_system_path` (0% null, 379 distinct): e.g., `TRAINING\A1\U12\Process\Pipelines\U12-2-`, `TRAINING\A1\U12\Process\Pipelines\U12-2-`, `TRAINING\A1\U12\Process\Pipelines\U12-2-`
- `centroid_x` (0% null): min=-37.50 p50=31.09 p95=86.12 max=102.83
- `centroid_y` (0% null): min=-28.96 p50=73.13 p95=183.62 max=192.66
- `centroid_z` (0% null): min=-5.60 p50=4.15 p95=12.51 max=20.97
- `bbox_volume_m3` (0% null): min=0.00 p50=0.01 p95=0.33 max=170.20
- `dry_weight_kg` (8% null): min=0.15 p50=10.89 p95=206.38 max=3484.54
- `design_pressure_kpa` (23% null): min=0.00 p50=0.00 p95=0.28 max=1206.58
- `design_temperature_c` (23% null): min=-23.15 p50=26.85 p95=256.00 max=260.00
- `mesh_quality` (0% null, 4 distinct): `full_mesh` (2,308, 75.4%), `fbx_supplemented` (590, 19.3%), `skipped_container` (153, 5.0%), `box_placeholder` (11, 0.4%)
- `mesh_uri` (0% null, 2,910 distinct): e.g., `mesh/0680b447-9986-5458-8148-323bb71cfdd`, `mesh/4d17925b-2739-5863-9348-53e70ba2f29`, `mesh/3fb29749-aa41-54d0-aead-8020ad9e182`
- `classification_confidence` (0% null, 2 distinct): `HIGH` (2,926, 95.6%), `LIKELY_BUG` (136, 4.4%)

### `bim_structural` (object)

- **Shape**: 4,840 rows × 219 cols
- **Column types**: 145 object, 41 float64, 21 bool, 12 int64
- **Completeness**: 200 cols ≥99% filled, 18 cols ≥50% null

**Key attributes**:
- `object_id` (0% null, 4,840 distinct): e.g., `a46b5040-c8f1-770e-439e-fc1d27527487`, `bcb7ee22-8a0b-776e-8796-64852ea341a3`, `7bf801ad-98ae-5894-884e-10acf6b2b699`
- `display_name` (0% null, 3,731 distinct): e.g., `Steel`, `MemberSystem-1-0151`, `MemberPartPrismatic-1-0241`
- `refined_class` (0% null, 1 distinct): `Structure` (4,840, 100.0%)
- `sp3d_pipeline` (0% null, 1 distinct): `` (4,840, 100.0%)
- `sp3d_system_path` (0% null, 2,203 distinct): e.g., ``, ``, `Electrical Device\Steel\MemberSystem-1-0`
- `centroid_x` (0% null): min=-25.15 p50=40.06 p95=72.80 max=106.20
- `centroid_y` (0% null): min=-27.55 p50=142.19 p95=185.46 max=191.46
- `centroid_z` (0% null): min=-0.73 p50=4.90 p95=10.47 max=14.68
- `bbox_volume_m3` (0% null): min=0.00 p50=0.22 p95=3.08 max=103778.77
- `dry_weight_kg` (65% null): min=0.00 p50=22.14 p95=657.02 max=147326.80
- `design_pressure_kpa`: all-null
- `design_temperature_c`: all-null
- `mesh_quality` (0% null, 3 distinct): `full_mesh` (2,577, 53.2%), `skipped_container` (2,181, 45.1%), `box_placeholder` (82, 1.7%)
- `mesh_uri` (0% null, 2,660 distinct): e.g., `mesh/a46b5040-c8f1-770e-439e-fc1d2752748`, ``, `mesh/7bf801ad-98ae-5894-884e-10acf6b2b69`
- `classification_confidence` (0% null, 1 distinct): `HIGH` (4,840, 100.0%)

### `bim_equipment` (object)

- **Shape**: 770 rows × 219 cols
- **Column types**: 145 object, 41 float64, 21 bool, 12 int64
- **Completeness**: 200 cols ≥99% filled, 18 cols ≥50% null

**Key attributes**:
- `object_id` (0% null, 770 distinct): e.g., `60b0703b-7860-5233-ab1f-fb310146c5d9`, `e51ad1ef-2d6e-56cf-9a43-34b9850cadd1`, `ebc5d324-1d04-f874-bd6f-98f3aca1c23c`
- `display_name` (0% null, 234 distinct): e.g., `TEST`, `TEST_copy`, `Equipment`
- `refined_class` (0% null, 1 distinct): `Equipment` (770, 100.0%)
- `sp3d_pipeline` (0% null, 1 distinct): `` (770, 100.0%)
- `sp3d_system_path` (0% null, 156 distinct): e.g., `TRAINING\A1\TEST`, `TRAINING\A1\TEST_copy`, ``
- `centroid_x` (0% null): min=-25.15 p50=39.59 p95=94.49 max=102.83
- `centroid_y` (0% null): min=-34.52 p50=126.81 p95=186.04 max=187.39
- `centroid_z` (0% null): min=-5.92 p50=4.38 p95=12.31 max=19.57
- `bbox_volume_m3` (0% null): min=0.00 p50=0.03 p95=72.69 max=21420.54
- `dry_weight_kg` (84% null): min=0.00 p50=300.00 p95=740.00 max=868.50
- `design_pressure_kpa`: all-null
- `design_temperature_c`: all-null
- `mesh_quality` (0% null, 4 distinct): `full_mesh` (584, 75.8%), `fbx_supplemented` (114, 14.8%), `skipped_container` (54, 7.0%), `box_placeholder` (18, 2.3%)
- `mesh_uri` (0% null, 717 distinct): e.g., `mesh/60b0703b-7860-5233-ab1f-fb310146c5d`, `mesh/e51ad1ef-2d6e-56cf-9a43-34b9850cadd`, `mesh/ebc5d324-1d04-f874-bd6f-98f3aca1c23`
- `classification_confidence` (0% null, 1 distinct): `HIGH` (770, 100.0%)

### `bim_electrical` (object)

- **Shape**: 1,053 rows × 219 cols
- **Column types**: 145 object, 41 float64, 21 bool, 12 int64
- **Completeness**: 200 cols ≥99% filled, 18 cols ≥50% null

**Key attributes**:
- `object_id` (0% null, 1,053 distinct): e.g., `512aa21c-2b1e-7c43-b649-60fb72efba86`, `7d8964e4-42a1-c7fe-2c57-7321f13252e7`, `e58dc73d-5a06-4e9b-9a52-15cd7f26c284`
- `display_name` (0% null, 807 distinct): e.g., `Electrical Device`, `Cable Trenches`, `Cable Trenches-1-0001`
- `refined_class` (0% null, 1 distinct): `Electrical` (1,053, 100.0%)
- `sp3d_pipeline` (0% null, 1 distinct): `` (1,053, 100.0%)
- `sp3d_system_path` (0% null, 250 distinct): e.g., ``, ``, ``
- `centroid_x` (0% null): min=0.97 p50=54.51 p95=88.57 max=103.84
- `centroid_y` (0% null): min=-20.10 p50=4.18 p95=124.12 max=187.41
- `centroid_z` (0% null): min=-2.36 p50=2.76 p95=8.19 max=13.82
- `bbox_volume_m3` (0% null): min=0.00 p50=0.08 p95=44.39 max=9360.41
- `dry_weight_kg` (80% null): min=0.30 p50=131.38 p95=624.18 max=2406.78
- `design_pressure_kpa`: all-null
- `design_temperature_c`: all-null
- `mesh_quality` (0% null, 4 distinct): `full_mesh` (738, 70.1%), `skipped_container` (167, 15.9%), `box_placeholder` (94, 8.9%), `fbx_supplemented` (54, 5.1%)
- `mesh_uri` (0% null, 887 distinct): e.g., ``, `mesh/7d8964e4-42a1-c7fe-2c57-7321f13252e`, `mesh/e58dc73d-5a06-4e9b-9a52-15cd7f26c28`
- `classification_confidence` (0% null, 1 distinct): `HIGH` (1,053, 100.0%)

### `bim_hvac` (object)

- **Shape**: 125 rows × 219 cols
- **Column types**: 145 object, 41 float64, 21 bool, 12 int64
- **Completeness**: 200 cols ≥99% filled, 18 cols ≥50% null

**Key attributes**:
- `object_id` (0% null, 125 distinct): e.g., `d725a4e1-b13a-1d4c-584d-a361802f1561`, `f856bddb-d4a3-33fb-d8b5-7c0e2c7d68a9`, `749ce098-03f7-0cc8-df51-65eab70fdbcd`
- `display_name` (0% null, 41 distinct): e.g., `HVAC`, `AHU`, `Supply`
- `refined_class` (0% null, 1 distinct): `HVAC` (125, 100.0%)
- `sp3d_pipeline` (0% null, 1 distinct): `` (125, 100.0%)
- `sp3d_system_path` (0% null, 20 distinct): e.g., ``, ``, ``
- `centroid_x` (0% null): min=-10.13 p50=-4.19 p95=38.08 max=50.52
- `centroid_y` (0% null): min=-34.82 p50=-31.30 p95=135.80 max=187.06
- `centroid_z` (0% null): min=-0.01 p50=4.19 p95=4.24 max=7.26
- `bbox_volume_m3` (0% null): min=0.00 p50=0.10 p95=6.18 max=935.06
- `dry_weight_kg` (58% null): min=2.73 p50=34.00 p95=745.95 max=2405.82
- `design_pressure_kpa`: all-null
- `design_temperature_c`: all-null
- `mesh_quality` (0% null, 3 distinct): `full_mesh` (78, 62.4%), `skipped_container` (37, 29.6%), `box_placeholder` (10, 8.0%)
- `mesh_uri` (0% null, 89 distinct): e.g., ``, ``, ``
- `classification_confidence` (0% null, 1 distinct): `HIGH` (125, 100.0%)

### `bim_other` (object)

- **Shape**: 2,159 rows × 219 cols
- **Column types**: 145 object, 41 float64, 21 bool, 12 int64
- **Completeness**: 200 cols ≥99% filled, 19 cols ≥50% null

**Key attributes**:
- `object_id` (0% null, 2,159 distinct): e.g., `8dd55e0a-2aee-5612-8465-b8f7ff0e7da3`, `d8743c3d-e544-d9f3-80b8-3aead8707baf`, `6a516c90-24d4-54ad-a736-271a8941c53e`
- `display_name` (0% null, 1,937 distinct): e.g., `For Review.nwd`, `Assy_FR_UC_CS_1-1-2`, `HgrAisc31_C3x6-1-C4`
- `refined_class` (0% null, 1 distinct): `Other` (2,159, 100.0%)
- `sp3d_pipeline` (0% null, 1 distinct): `` (2,159, 100.0%)
- `sp3d_system_path` (0% null, 378 distinct): e.g., ``, ``, `Assy_FR_UC_CS_1-1-2`
- `centroid_x` (0% null): min=-27.44 p50=24.03 p95=68.61 max=101.19
- `centroid_y` (0% null): min=-28.96 p50=132.14 p95=183.81 max=191.47
- `centroid_z` (0% null): min=-4.31 p50=4.48 p95=10.30 max=19.88
- `bbox_volume_m3` (0% null): min=0.00 p50=0.17 p95=1204.95 max=923841.68
- `dry_weight_kg` (88% null): min=0.00 p50=184.72 p95=1704.13 max=5493.13
- `design_pressure_kpa`: all-null
- `design_temperature_c`: all-null
- `mesh_quality` (0% null, 5 distinct): `full_mesh` (904, 41.9%), `skipped_container` (761, 35.2%), `box_placeholder` (456, 21.1%), `fbx_supplemented` (30, 1.4%), `line_mesh` (8, 0.4%)
- `mesh_uri` (0% null, 1,399 distinct): e.g., ``, `mesh/d8743c3d-e544-d9f3-80b8-3aead8707ba`, `mesh/6a516c90-24d4-54ad-a736-271a8941c53`
- `classification_confidence` (0% null, 1 distinct): `HIGH` (2,159, 100.0%)

### `bim_adjacent_to` (link)

- **Shape**: 110,173 rows × 7 cols
- **Column types**: 3 object, 3 float64, 1 bool
- **Completeness**: 7 cols ≥99% filled, 0 cols ≥50% null

**Key attributes**:
- **Columns**: `source_object_id`, `target_object_id`, `relation_type`, `distance_m`, `overlap_volume_m3`, `tolerance_m`, `is_symmetric`
- `source_object_id`: 8,312 distinct values
- `target_object_id`: 8,646 distinct values
- `relation_type`: `overlap` (87,553, 79.5%), `neartouch` (15,909, 14.4%), `touch` (6,711, 6.1%)

### `bim_has_parent` (link)

- **Shape**: 12,008 rows × 3 cols
- **Column types**: 2 object, 1 float64
- **Completeness**: 3 cols ≥99% filled, 0 cols ≥50% null

**Key attributes**:
- **Columns**: `child_object_id`, `parent_object_id`, `child_level`
- `child_object_id`: 12,008 distinct values
- `parent_object_id`: 3,974 distinct values

### `bim_belongs_to_pipeline` (link)

- **Shape**: 2,926 rows × 3 cols
- **Column types**: 3 object
- **Completeness**: 3 cols ≥99% filled, 0 cols ≥50% null

**Key attributes**:
- **Columns**: `object_id`, `pipeline_name`, `pipe_run_name`
- `object_id`: 2,926 distinct values

### `bim_in_group` (link)

- **Shape**: 12,009 rows × 3 cols
- **Column types**: 2 object, 1 bool
- **Completeness**: 3 cols ≥99% filled, 0 cols ≥50% null

**Key attributes**:
- **Columns**: `object_id`, `group_id`, `is_giant_group`
- `object_id`: 12,009 distinct values
- `group_id`: 3,355 distinct values

## Cross-Dataset Analysis

### 1. Object ID disjoint check

- `bim_piping`: 3,062 objects (overlap with earlier sets: 0)
- `bim_structural`: 4,840 objects (overlap with earlier sets: 0)
- `bim_equipment`: 770 objects (overlap with earlier sets: 0)
- `bim_electrical`: 1,053 objects (overlap with earlier sets: 0)
- `bim_hvac`: 125 objects (overlap with earlier sets: 0)
- `bim_other`: 2,159 objects (overlap with earlier sets: 0)
- **Total unique object_ids**: 12,009
- **Expected**: 12,009 (disjoint)
- **Total cumulative overlap**: 0  ✓ clean

### 2. `sp3d_system_path` prefix patterns

- `bim_piping`: top prefixes = `TRAINING` (2,926), `` (136)
- `bim_structural`: top prefixes = `TRAINING` (2,439), `` (2,397), `Electrical Device` (4)
- `bim_equipment`: top prefixes = `TRAINING` (697), `` (73)
- `bim_electrical`: top prefixes = `TRAINING` (792), `` (261)
- `bim_hvac`: top prefixes = `TRAINING` (68), `` (57)
- `bim_other`: top prefixes = `` (1,329), `TRAINING` (828), `Assy_FR_UC_CS_1-1-2` (2)

### 3. Shared `sp3d_system_path` across classes

- `bim_piping` ∩ `bim_structural`: **1** shared paths  (potential cross-class link)
- `bim_piping` ∩ `bim_equipment`: **1** shared paths  (potential cross-class link)
- `bim_piping` ∩ `bim_electrical`: **1** shared paths  (potential cross-class link)
- `bim_piping` ∩ `bim_hvac`: **1** shared paths  (potential cross-class link)
- `bim_piping` ∩ `bim_other`: **1** shared paths  (potential cross-class link)
- `bim_structural` ∩ `bim_equipment`: **1** shared paths  (potential cross-class link)
- `bim_structural` ∩ `bim_electrical`: **3** shared paths  (potential cross-class link)
- `bim_structural` ∩ `bim_hvac`: **1** shared paths  (potential cross-class link)
- `bim_structural` ∩ `bim_other`: **2** shared paths  (potential cross-class link)
- `bim_equipment` ∩ `bim_electrical`: **1** shared paths  (potential cross-class link)
- `bim_equipment` ∩ `bim_hvac`: **1** shared paths  (potential cross-class link)
- `bim_equipment` ∩ `bim_other`: **1** shared paths  (potential cross-class link)
- `bim_electrical` ∩ `bim_hvac`: **1** shared paths  (potential cross-class link)
- `bim_electrical` ∩ `bim_other`: **9** shared paths  (potential cross-class link)
- `bim_hvac` ∩ `bim_other`: **2** shared paths  (potential cross-class link)

### 4. Link Type connectivity

- `bim_adjacent_to`: 110,173 rows, cols: `source_object_id`, `target_object_id`, `relation_type`, `distance_m`, `overlap_volume_m3`, `tolerance_m`, `is_symmetric`
- `bim_has_parent`: 12,008 rows, cols: `child_object_id`, `parent_object_id`, `child_level`
- `bim_belongs_to_pipeline`: 2,926 rows, cols: `object_id`, `pipeline_name`, `pipe_run_name`
- `bim_in_group`: 12,009 rows, cols: `object_id`, `group_id`, `is_giant_group`

### 5. Group membership distribution

- Total groups: 3
- Largest group: 8,626 objects
- Singleton groups: 3,353
- Multi-element groups: 2

## Prior Findings (already known)

Skip re-discovering these. See `docs/findings/` for archives.

- **M1** (Piping misclassification): substring bug in DXTnavis regex. Fix applied; `classification_confidence` column marks affected rows.
- **M2** (Adjacency tiers): AABB-based → 3-tier classification (strong 13K / medium 87K / all 220K).
- **M3** (Parent box contamination): 448 hierarchy-container objects with `is_parent_box=True` skewed early adjacency counts.
- **M4** (FBX GUID mapping, 2026-04-15): 788 `fbx_supplemented` objects matched to GLB files via FBX Properties70 + centroid transform `Gold(x,y,z) = FBX(-x, z, y)`. 7 bonus SP3D columns found duplicated with XLSX; Gold schema unchanged. See `docs/findings/2026-04-15-M4-fbx-guid-mapping/`.
- 33 KPIs pre-computed (object/zone/pipeline/plant levels) in `src/bimkg/analytics/kpi.py`.
- 144 Louvain zones from spatial adjacency (`zones.py`).
- 147 distinct pipelines (`sp3d_pipeline` values).
- 3,355 connected groups (via `bim_in_group`).

## Suggested AI FDE Starting Prompts

Given M1–M4 are resolved, ask AI FDE:

1. Patterns in `display_name` that suggest semantic sub-categories
2. Anomalies in the `sp3d_bom_desc` text corpus (NLP angle)
3. Relationships between `sp3d_support_assembly` and `group_id`
4. Whether any pipeline has unexpectedly sparse `bim_adjacent_to` density
5. Objects whose bbox_volume + mesh_quality combo suggests mis-labeling
6. Does `sp3d_system_path` hierarchy suggest implicit Ontology namespaces?