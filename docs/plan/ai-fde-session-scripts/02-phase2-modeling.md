# Phase 2 세션 스크립트 — Ontology 모델링

**추천 설정**: Claude Opus · Ontology Modeler + Data Engineer skills · Ontology Query + Dataset Reader tools · Phase 1 요약 + foundry-dataset-profiles + M4 finding

**목표**: 6 Object Type + 4 Link Type의 **정교한 Ontology 설계**. Foundry UI 등록 전 설계도 확정.
**예상 소요**: 60–90분

**전제**: Phase 1 세션 완료, `docs/analysis/ai-fde-sessions/2026-04-15-phase1.md` 작성됨.

---

## Prompt 1 — Phase 1 결과 로딩

```
We completed Phase 1 exploration. Here's the summary:
[PASTE your Phase 1 summary markdown here]

Before we design the Ontology, confirm:
1. Do you recall the 11 datasets and their roles?
2. What was the most important finding from Phase 1?
3. What decisions are still open?

Once confirmed, we'll proceed to Object Type design.
```

---

## Prompt 2 — Object Type 설계 (개별)

반복 블록 (6개 Object Type 각각에 대해 실행):

```
Design the Foundry Ontology Object Type for `bim_piping`.

Provide:

1. **api_name** (code-friendly name, e.g., `BimPiping`)
2. **display_name** (user-facing, e.g., "Piping Component")
3. **title_property** (what shows as label in lists/3D viewer)
4. **description** (1–2 sentences for docs)

5. **Primary key**: `object_id` — confirm or suggest better

6. **Property classification** for the ~219 columns:
   - **Core** (always visible, indexed, searchable): 10–15 columns
   - **Extended** (visible but secondary): 30–50 columns
   - **Hidden** (internal, not shown to users): rest
   - **Typed specially**:
     * Media Reference: `mesh_uri` → `bim_mesh` Media Set
     * Geospatial: `centroid_x/y/z` and `bbox_min/max_x/y/z`?
     * Timestamp: `ingested_at_utc`, `sp3d_date_created`, `sp3d_date_last_modified`

7. **Property aliases** for user-friendly names
   (e.g., `sp3d_dry_weight` → "Dry Weight", `centroid_z` → "Elevation")

8. **Default query attributes** (what shows when someone clicks the object)

9. **Required properties** (must be non-null for valid object)

10. **Suggested derived properties** (not in source but computable)
    e.g., `is_heavy_object` = `dry_weight_kg > 1000`

Output as YAML so I can reference it during UI registration.
```

**실행 순서**: `bim_piping` → `bim_equipment` → `bim_structural` → `bim_electrical` → `bim_hvac` → `bim_other`

**기대**: 6개 상세 설계서가 생성됨. 저장: `docs/plan/ontology-design/object-types/`

---

## Prompt 3 — Link Type 설계

```
Now design the 4 Link Types.

For each Link Type, provide:

1. **api_name** (e.g., `adjacentTo`)
2. **display_name_forward** (A→B 방향 표시, e.g., "is adjacent to")
3. **display_name_reverse** (B→A 방향, e.g., "is adjacent to" if symmetric, else different)
4. **source_object_type** and **target_object_type**
   (if multi-type, can `bim_adjacent_to` span all 6 object types?)
5. **Cardinality**: one-to-one / one-to-many / many-to-many
6. **Symmetric**: yes/no
7. **Link-level properties** to carry (e.g., `distance_m`, `overlap_volume_m3`, `relation_type` for adjacency)
8. **Default display** in Object detail page (show top N, filter by property, etc.)
9. **Quality tier** (for `bim_adjacent_to`, strong/medium/all — how to surface?)

The 4 links:
- bim_adjacent_to       (110K rows, Object↔Object)
- bim_has_parent        (12K rows, Object→Object hierarchical)
- bim_belongs_to_pipeline (2.9K rows, Piping → Pipeline-as-object?)
- bim_in_group          (12K rows, Object → ConnectedGroup)

**Important**: `bim_belongs_to_pipeline` target is a pipeline identifier (string), not an existing Object Type.
Should we create a new `Pipeline` Object Type from the 147 distinct pipelines?

Same for `bim_in_group` → should we create a `ConnectedGroup` Object Type for the 3,355 groups?
```

**기대**: Link 설계서 + **누락된 Object Type 제안** (`Pipeline`, `ConnectedGroup`). 이게 중요한 발견.

---

## Prompt 4 — Interface 설계 (고급)

```
In Foundry Ontology, an **Interface** is a shared abstract type — useful when multiple Object Types share common properties.

My 6 BIM Object Types all have:
- object_id, display_name, centroid_x/y/z, bbox_*, mesh_uri, refined_class, adjacency_count, group_id, parent_id

Propose:

1. A **base Interface** `BIMObject` with all truly shared properties
2. Specialized **Interfaces** if some properties are shared by 2–3 types only
   (e.g., `Piping + Equipment` share pressure/temperature properties)
3. **Mixin** interfaces for cross-cutting concerns
   (e.g., `HasSP3DMetadata`, `HasMesh`, `HasPosition`)

For each Interface:
- api_name
- Required properties
- Optional properties
- Which Object Types implement it

This lets us query "all BIMObjects with bbox_volume > X" without listing 6 types.
```

**기대**: 3–5개 Interface 제안. Ontology의 깊이 증가.

---

## Prompt 5 — Action Type 설계

```
Foundry Actions let users (or Functions) MODIFY Ontology data.

For our BIM-KG, propose 3–5 useful Actions:

1. **Tag / annotate objects** (e.g., user marks "needs inspection")
2. **Adjust classification confidence** (manual override for M1 case)
3. **Link to external docs** (e.g., maintenance record)

For each Action:
- api_name
- Parameters (input)
- What Object Type(s) it modifies
- What changes (add property, create link, etc.)
- Who should have permission (end user vs. admin)
- Whether to integrate with AI FDE (auto-suggest when AI thinks it's appropriate)

Example structure:
  Action: TagForInspection
  Inputs: object_id, inspection_reason, deadline
  Effect: Creates new `inspection_tag` property on the object
```

**기대**: UI에서 사용자가 실제 데이터를 수정하는 워크플로우 발견.

---

## Prompt 6 — 설계 검증 & 리스크

```
Before I go to the UI and register all this, let's stress-test the design.

Please review everything we've designed and tell me:

1. **Internal inconsistencies** (naming, type, pattern mismatches)
2. **Performance concerns** (any Object Type or Link Type that will be slow?)
3. **Permission/governance gaps** (who can edit what)
4. **Migration risks** (if we change schema later, what breaks?)
5. **Foundry-specific gotchas** (e.g., Link cardinality constraints)

Then produce a **priority-ordered registration checklist**:
- What to register FIRST (to test the pipeline)
- What to register LAST (depends on previous)
- What can be deferred to Phase 3

Format: markdown checklist I can work through in the UI.
```

**기대**: 체크리스트 완성. `docs/plan/ontology-registration-checklist.md` 저장.

---

## Prompt 7 — 실행 가능한 스펙 문서

```
Produce a single markdown document I can hand to:
- A Foundry admin (to register the Ontology via UI)
- A future me (to understand my own design 6 months from now)
- AI FDE Phase 3 session (to build Functions/Agent on top)

Sections:
1. Overview (1 paragraph)
2. Object Types (6+, with YAML spec for each)
3. Interfaces (3–5)
4. Link Types (4+)
5. Action Types (3–5)
6. Open Questions (anything unresolved)
7. Implementation Order (registration checklist)

Keep it under 400 lines. Reference external docs (M4 finding, etc.) instead of inlining.
```

**기대**: `docs/plan/ontology-design-final.md` 생성. 이게 **Phase 7a 의 청사진**.

---

## 🎯 세션 종료 후 체크리스트

- [ ] 6 Object Types 각각 YAML 스펙 작성됨
- [ ] 4 Link Types 설계됨 (+ 혹시 `Pipeline`, `ConnectedGroup` 추가?)
- [ ] 3–5 Interfaces 제안됨
- [ ] Registration checklist 완성됨
- [ ] `docs/plan/ontology-design-final.md` 저장됨
- [ ] Phase 3로 넘어갈 준비됨 (실제 등록은 UI에서 직접)

---

## 🔄 AI FDE 가 헤맬 때 대응

### 증상 1: "Object Type / Interface / Link 의 차이를 잘 모름"
→ Foundry Ontology 공식 문서 URL을 대화에 포함:
```
Reference: https://palantir.com/docs/foundry/ontology/
```

### 증상 2: 219 컬럼을 전부 나열하려고 함
→ "Focus on the top 30 most important. We'll handle the rest in Phase 3."

### 증상 3: YAML 포맷이 불일치
→ "Use Foundry's Ontology YAML convention (snake_case api_name, camelCase property name)"
