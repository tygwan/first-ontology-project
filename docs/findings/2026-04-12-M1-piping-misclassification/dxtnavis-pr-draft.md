# DXTnavis PR Draft — Fix InferClass substring matching + expand data extraction

> **Target repository**: https://github.com/tygwan/DXTnavis
> **Target branch**: `main`
> **PR type**: Bug fix + Enhancement
> **Drafted**: 2026-04-12
> **Related downstream project**: [first-ontology-project](https://github.com/tygwan/first-ontology-project)
> **Evidence**: [M1 finding](README.md) with 4 figures, 5 data tables, reproducible audit script

This document is the **PR draft**. Copy the relevant sections into the actual
GitHub PR description when submitting.

---

## Summary

Two categories of changes to `Services/RefinedXlsxExporter.cs`:

1. **Bug fix**: `InferClass` uses case-insensitive **substring** matching which
   produces **997 false-positive Piping classifications** on the 2026-04-07
   snapshot (~34% inflation of the Piping class). Root cause: Piping keyword
   `"tee"` matches `"steel"`, and `"pipe"` matches `"Pipe Rack"` / `"Pipe Trench"`
   folder names in the system path. See `ANALYSIS` below for proof.

2. **Data extraction enhancement**: Expand the XLSX output so downstream
   consumers (knowledge graph / ontology pipelines / Palantir Foundry) can
   build on top of DXTnavis without needing to join multiple raw exports.
   Specifically: preserve `ParentId`, recover dropped SP3D properties,
   optionally emit Parquet, and standardize encodings.

---

## Part 1 — Bug fix: InferClass substring matching

### Current behavior

`InferClass` (lines 298-375) performs Tier 3 classification as:

```csharp
string combined = (sysPath + " " + displayName).ToLowerInvariant();
foreach (var key in objData.Keys)
{
    if (key.StartsWith("__")) continue;
    combined += " " + key.ToLowerInvariant();
}

if (combined.Contains("pipe") || combined.Contains("valve") ||
    combined.Contains("flange") || combined.Contains("elbow") ||
    combined.Contains("tee") || combined.Contains("reducer") ||
    combined.Contains("nozzle") || combined.Contains("coupling"))
    return "Piping";
```

### Problem

`.Contains()` is **substring** matching with no word boundaries. This causes:

| Intended keyword | Actually matches | Impact |
|------------------|------------------|-------:|
| `"tee"` (Tee pipe fitting) | **`"steel"`** (via `s-TEE-l`) | 10 steel structural members → Piping |
| `"pipe"` (Pipe fitting) | **`"Pipe Rack"`** folder (structural support) | 698 objects → Piping |
| `"pipe"` (Pipe fitting) | **`"Pipe Trench"`** folder (civil work) | 60 objects → Piping |
| `"pipe"` (Pipe fitting) | **`"Pipeline"`** folder (grouping node) | 12 objects → Piping |

### Concrete example

```
Object: MemberSystem-1-0151
System Path: For Review.nwd > Electrical Device > Steel > MemberSystem-1-0151
Navisworks properties: 항목|유형, 항목|이름, 항목|소스 파일, ... (8 Item metadata only)
SP3D properties: none
Current XLSX Class: Piping   ← BUG
Correct Class: Structure (steel member)
```

Because the system path contains "Steel", the `tee` keyword (intended for pipe Tee fittings) hits via substring match `s-TEE-l`. Piping is evaluated first in Tier 3, so Structure (which would match on the "steel" keyword) never gets a chance.

### Quantitative impact

On the 2026-04-07 snapshot (12,009 objects):

| Piping subset | Count | % of Piping |
|---------------|------:|------------:|
| HIGH confidence (has pipeline + commodity/spec/NPD metadata) | 2,926 | 72.9% |
| LOW confidence (has some metadata but no pipeline) | 91 | 2.3% |
| **LIKELY BUG** (no pipeline, no piping metadata) | **997** | **24.8%** |
| Total labeled Piping | 4,014 | 100% |

Cross-reference: the Structure class (5,926 objects) has **zero** `sp3d_pipeline` or `sp3d_eqp_type_0` set, so contamination is unidirectional (Piping absorbs misclassified Structure/Electrical, not the other way).

### Proposed fix

Replace `Contains` with **word boundary matching** using `Regex.IsMatch`:

```csharp
using System.Text.RegularExpressions;

// Compile once for performance
private static readonly Regex PipingKeywordRegex = new Regex(
    @"\b(pipe|valve|flange|elbow|tee|reducer|nozzle|coupling)\b",
    RegexOptions.IgnoreCase | RegexOptions.Compiled);

private static readonly Regex EquipmentKeywordRegex = new Regex(
    @"\b(equipment|vessel|pump|tank|compressor|exchanger|heater|reactor)\b",
    RegexOptions.IgnoreCase | RegexOptions.Compiled);

private static readonly Regex StructureKeywordRegex = new Regex(
    @"\b(struct|steel|beam|column|brace|foundation|slab|plate|grating|handrail|ladder|stair)\b",
    RegexOptions.IgnoreCase | RegexOptions.Compiled);

private static readonly Regex ElectricalKeywordRegex = new Regex(
    @"\b(electrical|cable|conduit|tray)\b",
    RegexOptions.IgnoreCase | RegexOptions.Compiled);

private static readonly Regex HvacKeywordRegex = new Regex(
    @"\b(hvac|duct|ventilat)\b",
    RegexOptions.IgnoreCase | RegexOptions.Compiled);

private static readonly Regex InstrumentationKeywordRegex = new Regex(
    @"\b(instrument)\b",
    RegexOptions.IgnoreCase | RegexOptions.Compiled);
```

And in `InferClass` Tier 3:

```csharp
string combined = (sysPath + " " + displayName).ToLowerInvariant();
foreach (var key in objData.Keys)
{
    if (key.StartsWith("__")) continue;
    combined += " " + key.ToLowerInvariant();
}

if (PipingKeywordRegex.IsMatch(combined))        return "Piping";
if (EquipmentKeywordRegex.IsMatch(combined))     return "Equipment";
if (StructureKeywordRegex.IsMatch(combined))     return "Structure";
if (ElectricalKeywordRegex.IsMatch(combined))    return "Electrical";
if (HvacKeywordRegex.IsMatch(combined))          return "HVAC";
if (InstrumentationKeywordRegex.IsMatch(combined)) return "Instrumentation";
return "Other";
```

**Note on `struct` keyword**: The existing list has `"struct"` as a Structure keyword, which would already match `"Structure"`, `"Structural"`, but `\bstruct\b` would NOT match `"Structural"` because of the word boundary. Consider expanding to `@"\b(struct|structural|structure)\b"` to preserve the original intent.

### Expected outcome

On the same 2026-04-07 snapshot after applying this fix:

| Class | Before (buggy) | After (fixed) | Delta |
|-------|---------------:|--------------:|------:|
| Piping | 4,014 | ~2,926 | -1,088 |
| Structure | 5,926 | ~6,900 | +974 |
| Electrical | 449 | ~510 | +61 |
| HVAC | 72 | ~72 | 0 |
| Equipment | 851 | ~851 | 0 |
| Other | 697 | ~750 | +53 |

The exact numbers depend on which Tier 3 keyword wins for each object after Piping false positives are removed, but the direction is clear: Piping shrinks to its HIGH-confidence subset, and the difference flows to Structure / Electrical.

### Tests to add

1. **Unit tests for substring regression**:
   ```csharp
   [Test] public void Tee_keyword_should_not_match_steel() {
       var result = InferClass(emptyProps, "Electrical Device > Steel > Member", "Member-1");
       Assert.That(result, Is.Not.EqualTo("Piping"));
       Assert.That(result, Is.EqualTo("Structure"));
   }

   [Test] public void Pipe_keyword_should_not_match_pipe_rack() {
       var result = InferClass(emptyProps, "> A1 > U12 > Civil > Pipe Rack", "Beam-1");
       Assert.That(result, Is.Not.EqualTo("Piping"));
       Assert.That(result, Is.EqualTo("Structure"));
   }

   [Test] public void Pipe_keyword_should_still_match_real_pipe() {
       var props = new Dictionary<string,string> { { "SmartPlant 3D|Pipeline", "P-001" } };
       var result = InferClass(props, "> Piping > P-001", "Pipe-1-0042");
       Assert.That(result, Is.EqualTo("Piping"));
   }
   ```

2. **Regression fixture**: Save the current 2026-04-07 classification as an expected-output fixture and run the fixed classifier against it. Assert that Piping shrinks and Structure grows.

3. **Snapshot replay test**: Re-run against existing sample projects and verify no real Pipe/Valve/Flange objects are demoted to Other.

---

## Part 2 — Data extraction wishlist

Downstream consumers need the following to build knowledge graphs and
ontology pipelines on top of DXTnavis output. These are grouped by
priority.

### MUST — blocking downstream Phase 2+

#### M2a. Preserve `ParentId` in XLSX output

**Current behavior**: `BuildDynamicColumns` (line 204-229) excludes any key starting with `__`, which drops the `__ParentId` meta field. The XLSX has no way to reconstruct the parent-child hierarchy.

**Impact**: Downstream consumers must join the XLSX with `AllProperties.csv` or `validation.csv` to recover ParentId, which is fragile (validation.csv only has 294/12,009 populated).

**Fix**:
- Add `ParentId` to the `MetaColumns` array (line 38-41)
- Alternatively, add it to the permitted metadata fields exported directly

#### M2b. Preserve `Level` as an integer column

**Current behavior**: Level is written as a string via `objData["__Level"] = record.Level.ToString()` and ends up as a text cell.

**Impact**: Downstream consumers must re-cast string to int per row.

**Fix**: Write `Level` as `ws.Cell(r, c).Value = record.Level` (int) instead of the string representation.

#### M2c. Emit a separate `Hierarchy` sheet

**Desired content**: 3 columns — `ObjectId(GUID)`, `ParentId`, `Level`.

**Rationale**: Even if the pivot sheet keeps ParentId, having a dedicated hierarchy sheet makes it trivial to build `HasParent` relationship datasets in ontology frameworks.

### SHOULD — significant quality-of-life for downstream

#### S2a. Recover dropped SP3D columns

**Currently missing from XLSX** (but present in `AllProperties_*.csv`):
- `SmartPlant 3D|Flow Direction` — critical for piping flow graph analysis
- `SmartPlant 3D|Cut length` (lowercase `l` — possibly a typo of `Cut Length`?)
- `ObjectId` (renamed to `ObjectId(GUID)` in XLSX, but also missing raw form)
- `객체이름` (Korean display name alternative)

**Fix**: Investigate why these are absent and ensure they flow through `TraverseAndExtractProperties`.

#### S2b. Resolve multi-category Pipeline name collision

**Current behavior**: `FindKey(columns, "Pipeline")` selects the first column whose PropertyName is "Pipeline", typically `SmartPlant 3D|Pipeline`. If other categories also have a "Pipeline" property, those are silently ignored.

**Impact**: The legacy C# SQLite backend found 157 distinct pipelines, but `RefinedXlsxExporter`'s Pipeline_Summary sheet reports only 146-147 (one row is the "Pipelines" label artifact). 10+ pipelines are lost for downstream summary consumers.

**Fix**: Either:
- Merge all "Pipeline"-named properties across categories into a union, or
- Emit all of them as separate columns with their category prefix

#### S2c. Filter placeholder "Pipelines" label from Pipeline field

**Current behavior**: 153 objects at Level 7 have `SmartPlant 3D|Pipeline = "Pipelines"` (the literal folder name from the hierarchy) rather than a real pipeline identifier.

**Impact**: `dim_pipeline` in downstream pipelines has a fake entry called "Pipelines" which confuses users.

**Fix**: When the Pipeline value exactly equals a parent folder name, emit an empty value or flag it.

#### S2d. Type-strict columns

**Current behavior**: All values are written as strings (`ws.Cell(r, c).Value = string`). Numeric values (weights, lengths, coordinates, counts) end up as text cells in Excel.

**Impact**: Downstream consumers have to re-parse every numeric field. Especially painful for weights like `"0 lbm"` (imperial string) vs floats.

**Fix**: Emit numeric fields as numbers. Decide on SI vs imperial policy per field.

### NICE-TO-HAVE — long-term enhancements

#### N2a. Parquet output option

**Request**: Add a `--format parquet` CLI flag that writes `Refining_ObjectID_<timestamp>.parquet` instead of `.xlsx`.

**Rationale**:
- Foundry and Spark-based tooling ingest Parquet natively
- Parquet preserves types (no string-only cells)
- File size is ~10x smaller for the same data
- The existing `ClosedXML` dependency would be replaced with `Parquet.Net` or `ChoETL`

**Current workaround**: Downstream project (`first-ontology-project`) converts XLSX → Parquet as a separate step.

#### N2b. Emit relationship sheets

**Desired output**:
- `AdjacentTo.csv` / sheet — spatial adjacency edges (already exists as `adjacency.csv` in a separate producer output; could be unified)
- `HasMaterial.csv` — object → material reference
- `HasSpecification.csv` — object → spec reference
- `BelongsToPipeline.csv` — piping component → pipeline (one-to-one mapping)
- `SupportedBy.csv` — equipment → supporting structure

**Rationale**: Knowledge graph pipelines need these as link datasets. Currently downstream code has to re-derive them from the property columns.

#### N2c. Canonical reference tables

**Desired output**:
- `Materials.csv` — distinct material names with canonical IDs
- `Specifications.csv` — distinct spec names with canonical IDs
- `Pipelines.csv` — distinct pipeline names (already have Pipeline_Summary, but as full canonical reference)

**Rationale**: Enables proper normalized joins instead of string-comparison joins. Foundry Ontology imports benefit from this structure.

#### N2d. Change tracking between exports

**Request**: When exporting, compare with the previous snapshot (if exists) and emit a `ChangeLog.csv`:
- Added objects (new ObjectIds)
- Removed objects (absent in new snapshot)
- Modified objects (same GUID, different properties)

**Rationale**: Plant models evolve over time. Downstream consumers need to know what changed between exports.

#### N2e. Embedded metadata sheet

**Desired output**: A `Metadata` sheet with:
- Export timestamp (UTC ISO 8601)
- DXTnavis version
- Source Navisworks file path + hash
- Export parameters (progress threshold, etc.)
- Row/column counts per sheet

**Rationale**: Provenance tracking. Makes it easy to audit "which XLSX produced this downstream result?"

---

## Compatibility and backward compatibility

- Part 1 (bug fix) **changes classification results** for existing projects. Users who have downstream dashboards keyed to the buggy counts will see changes. Recommend version bumping to v2.0.0 and documenting the change in `CHANGELOG.md`.
- Part 2 (data extraction) is **purely additive** where possible. Adding `ParentId` column, new sheets, or new CSV outputs does not break existing consumers.

---

## Testing strategy

1. Add unit tests for `InferClass` as shown in Part 1.
2. Run against all existing DXTnavis sample projects and snapshot the new class distributions.
3. Add a snapshot regression test that flags any change > 10% in any class count for a known project.
4. Cross-validate with the downstream Python port at
   `first-ontology-project/src/bimkg/ingest/xlsx_classifier.py` — this provides an independent reference implementation that can be kept in sync.

---

## Effort estimate

| Task | Effort |
|------|-------:|
| Part 1 InferClass fix + unit tests | 0.5 day |
| Regression test with snapshot fixture | 0.5 day |
| M2a/b/c hierarchy preservation | 0.5 day |
| S2a dropped SP3D columns | 0.5 day |
| S2b/c Pipeline collision fixes | 0.5 day |
| S2d type-strict columns | 1 day |
| Parquet output (N2a) | 1-2 days |
| Other N2b-e enhancements | 2-3 days |
| **Total (Parts 1+2 MUST+SHOULD)** | **~4 days** |
| **Total (including NICE-TO-HAVE)** | **~9 days** |

---

## Downstream validation

The `first-ontology-project` repository has an extensive test suite
(192 tests) that exercises the XLSX classification logic via a Python
port. After applying Part 1 (bug fix), re-run:

```bash
cd first-ontology-project
.venv/bin/python -m pytest tests/test_ingest/test_xlsx_classifier.py
```

The `test_oracle_100_percent_agreement` test compares the Python
classifier against the XLSX `Class` column. After the C# fix, update
the Python port keywords to use regex word boundaries as well, then
re-run the oracle test. A 100% match after both sides are fixed is the
acceptance criterion.

---

## Questions for review

1. Should the fix be backported to v1.x as a patch, or gated behind a
   v2.0.0 release?
2. Are there any known downstream consumers (other than `first-ontology-project`) that depend on the current buggy behavior?
3. What is the preferred way to handle the `struct` → `\bstruct\b`
   ambiguity? Expand to `\b(struct|structural|structure)\b`?
4. Is `ClosedXML` willing to be replaced with `Parquet.Net` for N2a,
   or should Parquet output be a separate optional module?
