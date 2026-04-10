# DXTnavis 2026-04-07 Baseline Insights

**Date**: 2026-04-07
**Source**: `data/raw/dxtnavis/2026-04-07/` + `data/working/dxtnavis/` (bundle import run)
**Method**: Six-level Python stdlib analysis under `scripts/analysis/260407/`

## Headline Numbers

| | |
|---|---|
| Total objects | **12,009** |
| Unique raw categories | 3,433 (65.7% collapsed into "Geometry Group") |
| Canonical classes (backend) | 5 — Other 49.3%, Piping 24.4%, Structure 14.9%, Support 6.0%, Equipment 5.5% |
| Objects with real mesh | 7,985 (66.5%) |
| Objects without mesh (container) | 3,353 (27.9%) |
| Objects with failed tessellation | 671 (5.6%, cause: `NoGeometry`) |
| Global site footprint | 145 m × 229 m × 28 m |
| Median object diagonal | 1.85 m |
| Pipelines | 157 (avg 18.6 objects/pipeline) |
| Producer spatial edges | 110,173 (overlap 79.5% / near-touch 14.4% / touch 6.1%) |
| Backend AABB spatial edges | 266,279 (containing 64.3% / overlapping 28.7% / touching 7.0%) |
| Backend recall vs producer | **85.6%** |
| Backend precision vs producer | **35.4%** |
| Connected groups | 3,355 (largest 8,626 = 71.8% of model; rest are 3,353 singletons + one 30-element subsystem) |

## Insight 1 — "Other" class is every bottleneck rolled into one

`Other` holds 5,917 objects (49.3% of the model). Inside it:

- 3,860 of those (65.2%) have no mesh or only a box placeholder, so they are containers, not physical objects.
- 3,200 of those (54.1% of Other) are isolated in the producer adjacency graph (degree 0).
- 88.8% of all producer spatial edges touch an Other object (Other-Other 31.5%, Other-Piping 23.3%, Other-Structure 22.1%, Other-Support 7.3%, Equipment-Other 4.6%).

The same objects appear in the three independent counts below:

| Source | Count |
|---|---|
| `connected_groups.csv` singleton groups | 3,353 |
| `validation.csv` rows where `AdjacencyCount = 0` | 3,353 (3,200 Other + 153 Piping) |
| `validation.csv` rows where `Verdict = SKIP_CONTAINER` | 3,353 |

**Three identities collapse into one rule**: *isolated && no mesh = container*.

### Implication

Split the backend `Other` class into two:

- **Container** — `HasRealMesh = false` AND producer adjacency count = 0. Expected count ≈ 3,353.
- **Uncategorized** — real mesh present, degree > 0, but no System/Pipeline/Equipment signal. Expected count ≈ 2,717.

Containers should not participate in spatial relation graphs, should not be edges in Neo4j projection, and should not compete with physical objects in schedule groupings. Doing this one split will:

- Drop the 3,353-singleton noise from the graph
- Simplify hub analysis (most false hubs are system containers)
- Shrink the backend false-positive ratio of AABB classification

## Insight 2 — Backend self-classification is measurably worse than producer

Pairwise comparison of the 110,173 producer adjacency pairs and the 266,279 backend AABB pairs:

|  | Producer | Backend AABB |
|---|---|---|
| Unique undirected pairs | 110,173 | 266,279 |
| Shared (intersection) | 94,326 | 94,326 |
| Only in source | 15,847 | 171,953 |

- **Backend recall on producer = 85.6%**: backend misses 14.4% of the real mesh-based pairs, mostly `near_touch` cases that backend cannot express.
- **Backend precision vs producer = 35.4%**: two thirds of backend's pairs are noise. The big contributor is backend's `containing` rule: 64.3% of backend pairs are `containing`, which almost always means "a container AABB encloses its children", not a real spatial relation.

### Implication

The planned `DXTnavis backend self-classified relation deprecation` item in `PLAN-TRACKER.md` is justified by these numbers. Ingest `adjacency.csv` directly and retire the AABB stage. The only capability the backend uniquely contributes is `containing`, and Insight 1 has already shown that most of those are false relations anyway.

## Insight 3 — The model has one physical plant and 3,353 loose containers

`connected_groups.csv` has an extremely skewed shape:

| Group rank | Element count |
|---|---|
| #1 | **8,626** |
| #2 | 30 |
| #3 – #3355 | 1 each |

The giant (8,626) contains:

| Class | Count | % of class |
|---|---|---|
| Structure | 1,791 | **100%** |
| Support | 715 | **100%** |
| Equipment | 652 | 98.8% |
| Piping | 2,756 | 94.2% |
| Other | 2,712 | 45.8% |
| **total** | **8,626** | **71.8% of model** |

Mesh quality inside the giant: 83.1% `full_mesh`, 9.0% `fbx_supplemented`, 7.7% `box_placeholder`, 0% `skipped_container`.

### Implication

4D simulation, clash detection, and spatial reasoning should all scope to the giant group, not to the full 12,009 model. Every other group is either the one 30-element auxiliary subsystem or one of the 3,353 administrative containers that were already identified in Insight 1.

## Insight 4 — Hierarchy level is a strong classification signal the backend ignores

`validation.csv` Level column distribution by class:

| Class | L0 | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Other | 1 | 4 | 8 | 34 | 112 | 592 | 2,216 | 1,629 | 1,047 | 274 |
| Piping | 0 | 0 | 0 | 0 | 0 | 0 | 37 | 1,880 | 1,009 | 0 |
| Structure | 0 | 0 | 134 | 0 | 4 | 15 | 177 | 669 | 744 | 48 |
| Support | 0 | 0 | 2 | 0 | 0 | 1 | 293 | 251 | 168 | 0 |
| Equipment | 0 | 0 | 0 | 0 | 0 | 32 | 597 | 31 | 0 | 0 |

Signals:

- **Piping only exists at L6-L8**. An object at L0-L5 or L9 cannot be piping.
- **Equipment peaks at L6 (597 of 660 = 90.5%)** and is absent above L8.
- **Structure has two modes**: a small L2 cluster (134 objects, probably floor-level structural containers) and a long L4-L9 tail.
- **Support spans only L2 and L6-L8**.

### Implication

The current refining heuristic in `DxtnavisSemanticStore.DeriveObjectClass` relies on System/Pipeline/Equipment keyword checks. Adding Level as a guard (e.g. "cannot be Piping unless level in [6, 7, 8]") will measurably reduce the 49.3% Other population without needing new producer data.

## Insight 5 — Pipeline, not Class, is the real schedule axis

The current schedule run creates 5 tasks that are literally the 5 canonical classes. All 12,009 objects are placed, no object is multi-assigned, but the tasks are an identity partition of the class column — they carry no construction semantics.

Pipeline column tells a different story:

- 157 distinct pipelines inside the Piping class
- 2,926 piping objects distributed with an **average of 18.6 objects per pipeline**
- The largest pipeline (`P-10147`) has only 129 objects — none of the pipelines are runaway containers
- Non-Piping classes (Structure, Equipment, Support) also have their own grouping columns (`SystemPath` at 64.6% fill, `ConstructionType` at 29%, `EquipmentName` at 4.2%)

### Implication

The next `schedule/generate` call should be re-run with:

- `groupBy = Pipeline` for piping (157 tasks, natural construction unit)
- fallback `groupBy = SystemPath` or `ConstructionType` for non-piping classes

This is a one-call change that needs no new code — the existing schedule endpoint already accepts `groupBy`. The class-grouped run can stay as a sanity baseline.

## Insight 6 — Silent backend parsing bugs

Two separate signals show that `DxtnavisSemanticStore.ParseAllProperties` is dropping fields it should be capturing:

1. **`SourceFileName` fill rate = 0.008% (1/12,009)** while `SourceFilePath` = 99.99%. The raw column `항목|소스 파일` is 100% filled. The canonical pass is extracting path but losing name.
2. **153 of 660 Equipment objects (23.2%) have empty `EquipmentName`**. The heuristic classifies the object as Equipment but cannot recover its name.

Neither is fatal for the current bundle import run, but both weaken the canonical schema. These should be fixed when the refining parser is touched next.

## Insight 7 — Raw category is useless; System/Pipeline names are not

The 12,009 objects span 3,433 raw categories, but:

- 65.7% are lumped into `Geometry Group`
- 10 of the top 15 categories have 4-10 objects each
- Classic Revit categories (`Equipment`, `Beams`, `Columns`, `Structural`, `Electrical`, `Footings`) have fewer than 10 objects each

In contrast, naming patterns are extremely informative. Examples of pipeline names that are themselves classifiers: `Refining Pipe Rack-4-GLP-0102-1C0031`, `Distillation Unit B01-2-W-0101-1C0031`, `B01-Structure-Columns`, `PR01-ElectricalSystems`. The top hub of the producer graph after "Obstruction Volume" is literally `S1211-EquipmentSystems` with 3,532 edges — an object whose **name** already announces its class and system.

### Implication

Any future refining classifier should prefer name pattern matching (regex over display name + pipeline + system path) over the raw Navis category column. The category column is almost information-free for this particular export.

## Insight 8 — "Obstruction Volume" is polluting the graph

The single highest-degree node in the producer adjacency graph is an object named `Obstruction Volume` with **degree 5,267** — about 3× the next hub. This is a clash-detection bounding volume, not a physical object. It is touching nearly half the model by design.

### Implication

Add a display-name / category blacklist during adjacency ingestion so objects named `Obstruction Volume`, `Insulation Volume` (145 objects), and similar analytical volumes are either excluded from the graph or tagged as `analysis-volume` and dropped from Neo4j edges. Without this filter, any degree-centrality or clustering analysis on the graph will be dominated by these synthetic objects.

## Insight 9 — Mesh quality has a clean size signature

Cross-tab of bbox diagonal length vs mesh quality:

| size | full_mesh | fbx | line | box | skip | total |
|---|---|---|---|---|---|---|
| < 0.1 m | 180 | 4 | 0 | 0 | 0 | 184 |
| 0.1-0.5 m | 1,962 | 548 | 8 | 26 | 139 | 2,683 |
| 0.5-2 m | 2,222 | 157 | 0 | 149 | 716 | 3,244 |
| 2-5 m | 1,539 | 47 | 0 | 111 | 1,223 | 2,920 |
| 5-20 m | 1,185 | 30 | 0 | 217 | 1,132 | 2,564 |
| 20-100 m | 100 | 2 | 0 | 163 | 137 | 402 |
| ≥ 100 m | 1 | 0 | 0 | 5 | 6 | 12 |

Three patterns:

- **Small objects (< 0.5 m) are almost always full mesh.** Fittings and bolts ship as meshes.
- **Mid-size objects (2-20 m) are dominated by `skipped_container`.** Containers carry large bounding boxes.
- **Huge objects (≥ 20 m) are almost entirely box placeholder or skipped container.** Site-level aggregates.

### Implication

Instead of treating mesh quality as a per-object validation verdict, it can be used as a cheap structural classifier when Insight 1's container-split is not enough: any object ≥ 5 m whose mesh is `box_placeholder` is almost certainly a container even if it is not singleton in the adjacency graph.

## Concrete Follow-ups Ranked by Value

1. **Split `Other` into `Container` and `Uncategorized` (Insight 1)** — uses only producer data, no new parser. Drops 3,353 objects out of the physical-object scope, dramatically improving the signal-to-noise ratio of every subsequent analysis. Estimated refining code change: small.

2. **Ingest `adjacency.csv` and deprecate backend AABB classification (Insight 2)** — already the agreed highest-value next step and now numerically justified. Producer is higher precision *and* higher semantic quality (overlap volume, mesh-based touch distinction).

3. **Add display-name/category blacklist for `Obstruction Volume`, `Insulation Volume`, other analytical volumes (Insight 8)** — one-line filter, prevents graph pollution.

4. **Re-run schedule with `groupBy = Pipeline` for Piping, fallback to `SystemPath`/`ConstructionType` for others (Insight 5)** — no code change, one API call, converts the current identity-partition into a meaningful construction axis.

5. **Add `Level` as a refining heuristic guard (Insight 4)** — reduces `Other` further without touching Level's own schema.

6. **Fix `SourceFileName` and `EquipmentName` extraction (Insight 6)** — silent bugs in ParseAllProperties.

7. **Prefer name pattern over raw category in refining (Insight 7)** — the category column is almost information-free for this export.

## Not-worth-doing (for now)

- Running a visualization library on the full 12,009 model before doing step 1. The 3,353 containers will dominate any 2D/3D scatter.
- Extending the AABB classifier. Insight 2 has shown it is a worse classifier, not a smaller one. Extending is sunk cost.
- Ingesting `spatial_relationships.ttl` directly. Insight 2 has shown that producer `adjacency.csv` carries the same information in a denormalized but simpler form. TTL is useful only if a downstream consumer actually needs RDF, which is still undecided.

## Scripts Used

All analysis is reproducible:

```
scripts/analysis/260407/level1_basics.py
scripts/analysis/260407/level2_properties.py
scripts/analysis/260407/level3_spatial.py
scripts/analysis/260407/level4_relations.py
scripts/analysis/260407/level5_schedule.py
scripts/analysis/260407/level6_cross.py
```

Outputs are captured next to each script as `level*_output.txt`. Rerun any level with `python scripts/analysis/260407/levelN_*.py` from the repo root.
