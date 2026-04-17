"""M6 finding audit — Ontology Registration 비대칭 실패 재현용.

6개 Object Type parquet 을 스캔하여 다음을 리포트:
1. `null` Arrow dtype 컬럼 개수 + spec 교집합 (null-dtype 이론 기각 근거)
2. `sp3d_sp3d_moniker` vs `sp3d_moniker` 컬럼 존재 (이중 prefix 이슈)
3. `mesh_uri` 샘플 값의 `mesh/` prefix (Media Reference path 불일치)
4. `ingested_at_utc` Arrow type (M5 regression 감지)

Usage:
    .venv/bin/python docs/findings/2026-04-17-M6-ontology-registration-asymmetry/audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[3]
BASE = REPO / "data" / "ontology" / "2026-04-12" / "object_types"
EVIDENCE = Path(__file__).parent / "evidence"
EVIDENCE.mkdir(exist_ok=True)

# Spec from docs/plan/ontology-registration-cheatsheet.md §2.1-2.6
BIM_OBJECT_34 = [
    "object_id", "display_name", "title", "refined_class", "original_class",
    "classification_confidence", "classification_confidence_reason",
    "system_path", "parent_id", "group_id",
    "centroid_x", "centroid_y", "centroid_z",
    "bbox_min_x", "bbox_min_y", "bbox_min_z",
    "bbox_max_x", "bbox_max_y", "bbox_max_z",
    "bbox_volume_m3", "mesh_uri", "mesh_quality", "has_real_mesh",
    "vertex_count", "triangle_count", "adjacency_count", "dry_weight_kg",
    "is_container", "is_parent_box", "is_bbox_placeholder", "is_hidden",
    "graph_participant", "has_own_geometry", "verdict",
]
SP3D_META_3 = ["sp3d_sp3d_moniker", "sp3d_name", "sp3d_status"]
PRESSURE_TEMP_2 = ["design_pressure_kpa", "design_temperature_c"]
NAV_META_6 = [
    "nav_item_source_file_name", "nav_item_type", "nav_class_display_name",
    "level_val", "is_leaf", "child_count",
]

PIPING_18 = [
    "sp3d_pipeline", "sp3d_pipe_run", "sp3d_npd", "sp3d_flow_direction",
    "sp3d_description", "sp3d_commodity_code", "sp3d_construction_type",
    "sp3d_location", "sp3d_short_code", "sp3d_reporting_type",
    "npd_end1_m", "npd_end2_m", "length_m",
    "sp3d_insulation_purpose", "sp3d_insulation_thickness",
    "refining_rule", "refining_rule_version", "nav_item_guid",
]
STRUCTURAL_14 = [
    "sp3d_material", "sp3d_material_name", "sp3d_material_type",
    "sp3d_section_name", "width_m", "depth_m",
    "sp3d_fireproofing_label", "sp3d_fire_rating",
    "sp3d_description", "sp3d_location", "sp3d_reporting_type",
    "refining_rule", "refining_rule_version", "nav_item_guid",
]
EQUIPMENT_10 = [
    "sp3d_equipment_name", "sp3d_type", "sp3d_eqp_type_0", "sp3d_eqp_type_1",
    "sp3d_eqp_type_2", "sp3d_location", "sp3d_area",
    "refining_rule", "refining_rule_version", "nav_item_guid",
]
ELECTRICAL_8 = [
    "sp3d_description", "sp3d_commodity_code", "length_m", "sp3d_location",
    "sp3d_short_code", "refining_rule", "refining_rule_version", "nav_item_guid",
]
HVAC_7 = [
    "sp3d_type", "sp3d_description", "length_m", "sp3d_location",
    "refining_rule", "refining_rule_version", "nav_item_guid",
]
OTHER_2 = ["refining_rule", "refining_rule_version"]

SPECS = {
    "piping":     BIM_OBJECT_34 + SP3D_META_3 + PRESSURE_TEMP_2 + PIPING_18     + NAV_META_6,
    "structural": BIM_OBJECT_34 + SP3D_META_3                  + STRUCTURAL_14 + NAV_META_6,
    "equipment":  BIM_OBJECT_34 + SP3D_META_3                  + EQUIPMENT_10  + NAV_META_6,
    "electrical": BIM_OBJECT_34 + SP3D_META_3                  + ELECTRICAL_8  + NAV_META_6,
    "hvac":       BIM_OBJECT_34 + SP3D_META_3                  + HVAC_7        + NAV_META_6,
    "other":      BIM_OBJECT_34 + SP3D_META_3                  + OTHER_2       + NAV_META_6,
}


def main() -> int:
    rows = []
    for t, spec in SPECS.items():
        path = BASE / f"{t}.parquet"
        if not path.exists():
            print(f"[MISSING] {path}", file=sys.stderr)
            continue

        schema = pq.read_schema(path)
        meta = pq.read_metadata(path)
        types = {f.name: str(f.type) for f in schema}
        null_cols = {name for name, ty in types.items() if ty == "null"}
        spec_set = set(spec)
        hit = sorted(null_cols & spec_set)

        # sp3d_moniker rename check
        has_old = "sp3d_sp3d_moniker" in types
        has_new = "sp3d_moniker" in types

        # mesh_uri prefix check
        mesh_prefix_status = "—"
        if "mesh_uri" in types:
            df = pd.read_parquet(path, columns=["mesh_uri"])
            sample = df["mesh_uri"].dropna().head(1)
            if len(sample):
                v = str(sample.iloc[0])
                mesh_prefix_status = "🔴 mesh/" if v.startswith("mesh/") else "✅ clean"
            else:
                mesh_prefix_status = "empty"

        # ingested_at_utc type (M5 regression check)
        ing = types.get("ingested_at_utc", "—")
        ing_status = "✅ string" if "string" in ing else f"🔴 {ing[:25]}"

        rows.append({
            "type": t,
            "rows": meta.num_rows,
            "total_cols": len(types),
            "null_cols": len(null_cols),
            "spec_cols": len(spec_set),
            "null_in_spec": len(hit),
            "null_in_spec_names": ",".join(hit),
            "has_sp3d_sp3d_moniker": has_old,
            "has_sp3d_moniker": has_new,
            "mesh_uri_prefix": mesh_prefix_status,
            "ingested_at_utc_type": ing_status,
        })

    df = pd.DataFrame(rows)
    csv_path = EVIDENCE / "registration_audit.csv"
    df.to_csv(csv_path, index=False)

    print(f"{'type':<12} {'rows':>6} {'cols':>5} {'null':>5} {'spec':>5} {'null∩spec':>10} {'moniker':<15} {'mesh_uri':<12} {'ingested':<20}")
    print("-" * 120)
    for r in rows:
        moniker = (
            "🔴 old" if r["has_sp3d_sp3d_moniker"] and not r["has_sp3d_moniker"]
            else "✅ renamed" if r["has_sp3d_moniker"]
            else "—"
        )
        print(
            f"{r['type']:<12} {r['rows']:>6,} {r['total_cols']:>5} {r['null_cols']:>5} "
            f"{r['spec_cols']:>5} {r['null_in_spec']:>10} "
            f"{moniker:<15} {r['mesh_uri_prefix']:<12} {r['ingested_at_utc_type']:<20}"
        )
    print(f"\n→ Evidence CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
