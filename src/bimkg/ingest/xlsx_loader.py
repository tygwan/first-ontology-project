"""Load and normalize the DXTnavis RefinedXlsxExporter output.

This module reads ``Refining_ObjectID_<timestamp>.xlsx`` (Sheet:
``Refining_ObjectID_Pivot``) and renames its 135 columns to snake_case so
they can be written to Parquet/SQLite and imported into Palantir Foundry.

Column normalization strategy
-----------------------------
1. **Explicit renames** (``EXPLICIT_RENAMES``) cover:
   - 5 meta columns added by the exporter (Class, ObjectId(GUID), ...)
   - 14 ``항목|*`` (Navisworks Item metadata)
   - 14 ``재질|*`` (Navisworks Material rendering colors)
   - 8  ``형상|*`` (Navisworks geometry statistics)
2. **Programmatic rule** for ``SmartPlant 3D|<PropertyName>``:
   strip the prefix, run ``_snake_case`` on the name, and prepend ``sp3d_``.
3. **Fallback**: any other column with a ``|`` gets ``<category>_<name>``;
   anything without ``|`` gets plain snake_case.

After renaming, ``normalize_columns`` checks for duplicate output names and
raises ``ValueError`` with the colliding originals. This guarantees that the
resulting DataFrame has unique column names safe for Parquet.

The XLSX ``Class`` column is renamed to ``class_raw`` rather than ``class``
because ``class`` is a Python keyword and because downstream Gold-layer code
will derive ``original_class`` / ``refined_class`` / ``refining_rule`` from
this value.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Explicit column renames
# ---------------------------------------------------------------------------

EXPLICIT_RENAMES: dict[str, str] = {
    # Meta (first 5 columns of XLSX, added by the exporter)
    "Class": "class_raw",
    "ObjectId(GUID)": "object_id",
    "DisplayName": "display_name",
    "System Path": "system_path",
    "Level": "level",
    # 항목 | Navisworks Item metadata (14 columns)
    "항목|GUID": "nav_item_guid",
    "항목|유형": "nav_item_type",
    "항목|내부 유형": "nav_item_internal_type",
    "항목|이름": "nav_item_name",
    "항목|아이콘": "nav_item_icon",
    "항목|소스 파일": "nav_item_source_file",
    "항목|소스 파일 이름": "nav_item_source_file_name",
    "항목|파일 이름": "nav_item_file_name",
    "항목|도면층": "nav_item_layer",
    "항목|단위": "nav_item_unit",
    "항목|재질": "nav_item_material",
    "항목|작성자": "nav_item_author",
    "항목|숨김": "nav_item_hidden",
    "항목|필수": "nav_item_required",
    # 재질 | Navisworks Material rendering colors (14 columns)
    "재질|분산.빨간색": "nav_material_diffuse_r",
    "재질|분산.녹색": "nav_material_diffuse_g",
    "재질|분산.파란색": "nav_material_diffuse_b",
    "재질|반사.빨간색": "nav_material_specular_r",
    "재질|반사.녹색": "nav_material_specular_g",
    "재질|반사.파란색": "nav_material_specular_b",
    "재질|발광.빨간색": "nav_material_emissive_r",
    "재질|발광.녹색": "nav_material_emissive_g",
    "재질|발광.파란색": "nav_material_emissive_b",
    "재질|주변.빨간색": "nav_material_ambient_r",
    "재질|주변.녹색": "nav_material_ambient_g",
    "재질|주변.파란색": "nav_material_ambient_b",
    "재질|광택": "nav_material_shininess",
    "재질|투명도": "nav_material_transparency",
    # 형상 | Navisworks geometry stats (8 columns)
    "형상|삼각형": "nav_geom_triangles",
    "형상|기본체": "nav_geom_primitives",
    "형상|솔리드": "nav_geom_solids",
    "형상|조각": "nav_geom_fragments",
    "형상|선": "nav_geom_lines",
    "형상|점": "nav_geom_points",
    "형상|스냅점": "nav_geom_snap_points",
    "형상|문자": "nav_geom_text",
}


# ---------------------------------------------------------------------------
# snake_case conversion
# ---------------------------------------------------------------------------


def _snake_case(s: str) -> str:
    """Convert PascalCase / camelCase / spaced / mixed names to snake_case.

    Examples:
        "Dry Weight"    -> "dry_weight"
        "PipeRun"       -> "pipe_run"
        "NPD"           -> "npd"
        "DryCGX"        -> "dry_cgx"
        "Eqp Type 0"    -> "eqp_type_0"
        "BOM description" -> "bom_description"
        "Spec Name"     -> "spec_name"
    """
    # Insert underscore between a lowercase/digit and an uppercase letter:
    #   "aB"      -> "a_B"
    #   "Dry2x"   -> no change (no change between lower and digit)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    # Insert underscore between sequences of uppercase and uppercase+lowercase:
    #   "ABc"     -> "A_Bc"
    #   "DryCGX"  -> "Dry_CGX" (but the previous rule already split y->C)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    # Replace any run of non-word characters with a single underscore
    s = re.sub(r"[^\w]+", "_", s)
    # Lowercase
    s = s.lower()
    # Collapse duplicate underscores and trim leading/trailing
    s = re.sub(r"_+", "_", s).strip("_")
    return s


# ---------------------------------------------------------------------------
# Per-column normalization
# ---------------------------------------------------------------------------


def normalize_column_name(name: str) -> str:
    """Normalize a single raw column name to snake_case.

    Priority:
        1. Exact match in ``EXPLICIT_RENAMES``
        2. ``"SmartPlant 3D|<prop>"`` -> ``"sp3d_<snake(prop)>"``
        3. Other ``"<cat>|<prop>"``    -> ``"<snake(cat)>_<snake(prop)>"``
        4. No pipe -> ``_snake_case(name)``
    """
    if name in EXPLICIT_RENAMES:
        return EXPLICIT_RENAMES[name]

    if "|" in name:
        category, prop = name.split("|", 1)
        if category == "SmartPlant 3D":
            return "sp3d_" + _snake_case(prop)
        return _snake_case(category) + "_" + _snake_case(prop)

    return _snake_case(name)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` with every column renamed via ``normalize_column_name``.

    Raises ``ValueError`` if the normalization produces two or more columns
    with the same name — callers can then either extend ``EXPLICIT_RENAMES``
    or choose new suffixes.
    """
    new_names = {col: normalize_column_name(col) for col in df.columns}
    values = list(new_names.values())

    duplicates = {v for v in values if values.count(v) > 1}
    if duplicates:
        collisions: dict[str, list[str]] = {}
        for orig, new in new_names.items():
            if new in duplicates:
                collisions.setdefault(new, []).append(orig)
        raise ValueError(
            f"Column name collisions after normalization: {collisions}"
        )

    return df.rename(columns=new_names)


# ---------------------------------------------------------------------------
# XLSX loader
# ---------------------------------------------------------------------------


def load_xlsx_pivot(xlsx_path: Path) -> pd.DataFrame:
    """Load the ``Refining_ObjectID_Pivot`` sheet and normalize its columns.

    Returns a DataFrame of shape (12,009, 135) with snake_case column names.
    The ``Class`` column becomes ``class_raw`` (used later to derive
    ``original_class`` and ``refined_class`` in the lineage scheme).
    """
    df = pd.read_excel(xlsx_path, sheet_name="Refining_ObjectID_Pivot")
    return normalize_columns(df)
