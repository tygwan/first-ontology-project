# DXTnavis Issue Draft — adjacency.csv includes non-geometry hierarchy nodes

## Title

`adjacency.csv includes hierarchy nodes without geometry, causing 66% false-positive edges`

## Body

### Problem

`adjacency.csv` includes objects that have no actual mesh geometry but have aggregated bounding boxes inherited from their children. These objects are hierarchy nodes (system groups, area containers) at Levels 0–5, not physical components.

**Impact**: 448 such objects generate 145,346 false-positive adjacency edges (66% of total 220,346). The worst offender is `Structure` (Level 1, bbox 103,779 m³ = 47m cube) with degree 5,267 — connected to 62% of all physical objects.

### Examples

| Object | Level | Class | BBox volume | Degree | Has mesh |
|--------|------:|-------|------------:|-------:|:--------:|
| Structure | 1 | Structure | 103,779 m³ | 5,267 | No |
| A2 | 2 | Other | 209,726 m³ | ~3,000 | No |
| U15 | 3 | Other | 144,375 m³ | ~2,000 | No |
| Equipment | 4 | Equipment | 2,593 m³ | ~500 | No |
| Cable Trenches | 5 | Electrical | 625 m³ | ~200 | No |

These objects are hierarchy containers — their bounding boxes encompass all children.

### Current workaround

We detect parent boxes in Python with:
```python
is_parent_box = (has_real_mesh == False) AND (bbox_volume > 99th percentile of mesh objects)
```
And exclude them from graph analysis. This works but is heuristic.

### Suggested fix (pick one)

**Option A** (preferred): Filter `adjacency.csv` to only include objects with `HasMesh = true` (from geometry.csv). This preserves hierarchy in other files while removing false adjacency.

**Option B**: Add a `hasGeometry: bool` column to `adjacency.csv` so consumers can filter.

**Option C**: Add an `isHierarchyNode: bool` column to the main objects export.

### Questions

1. Are these objects intentionally included in adjacency, or is this a side effect of processing all Navisworks elements?
2. If removed from adjacency, would `connected_groups.csv` also change? (Groups are computed from adjacency)
3. Are there cases where a meshless hierarchy node should legitimately participate in adjacency? (e.g., a system boundary that physically exists as a plate)

### Context

- Finding M3 in `first-ontology-project`
- The same degree-5,267 outlier was noted in our baseline analysis (Insight 8) but root cause was unidentified until now
- After filtering, our graph drops from 8,511 → 7,840 nodes and max degree from 5,161 → 388
