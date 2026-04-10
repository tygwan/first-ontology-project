"""Python port of RefinedXlsxExporter.InferClass (C#).

This module is a **1:1 reproduction** of the classification logic in
``DXTnavis/Services/RefinedXlsxExporter.cs`` (main branch).

Its purpose is **oracle validation**: given the same input (SP3D properties,
system path, display name), this function must produce the exact same class
label that the RefinedXlsxExporter wrote into the snapshot XLSX file.

If ``infer_class(obj_props, obj_sys_path, obj_display_name)`` ever disagrees
with the XLSX ``Class`` column for any of the 12,009 objects, either:
  1. The C# logic has changed and this port is stale → update the constants.
  2. Our input recovery is wrong → review how properties are extracted from
     the AllProperties CSV.
  3. There is a bug in the C# logic itself → document as an accepted deviation.

Reference: docs/analysis/refined-xlsx-exporter-logic.md
"""

from __future__ import annotations

from typing import Mapping

# ---------------------------------------------------------------------------
# Keyword lists -- these must match the C# source exactly (order preserved)
# ---------------------------------------------------------------------------

PIPING_KEYWORDS: tuple[str, ...] = (
    "pipe", "valve", "flange", "elbow", "tee", "reducer", "nozzle", "coupling",
)

EQUIPMENT_KEYWORDS: tuple[str, ...] = (
    "equipment", "vessel", "pump", "tank", "compressor",
    "exchanger", "heater", "reactor",
)

STRUCTURE_KEYWORDS: tuple[str, ...] = (
    "struct", "steel", "beam", "column", "brace", "foundation",
    "slab", "plate", "grating", "handrail", "ladder", "stair",
)

ELECTRICAL_KEYWORDS: tuple[str, ...] = (
    "electrical", "cable", "conduit", "tray",
)

HVAC_KEYWORDS: tuple[str, ...] = (
    "hvac", "duct", "ventilat",
)

INSTRUMENTATION_KEYWORDS: tuple[str, ...] = (
    "instrument",
)


# ---------------------------------------------------------------------------
# Helper: clean "DisplayString:" prefix
# ---------------------------------------------------------------------------

def clean_display_string(value: str | None) -> str:
    """Port of ``RefinedXlsxExporter.CleanDisplayString``.

    Strips the ``DisplayString:`` prefix if present, case-insensitively.
    Returns an empty string for None/empty input.
    """
    if value is None or value == "":
        return ""
    if value.lower().startswith("displaystring:"):
        return value[len("DisplayString:"):].strip()
    return value


# ---------------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------------

def _split_property_name(key: str) -> str:
    """Return the part after ``|`` in a ``"Category|PropertyName"`` key.

    If no pipe is present, return the key unchanged.
    """
    idx = key.find("|")
    return key[idx + 1:] if idx >= 0 else key


def infer_class(
    properties: Mapping[str, str],
    sys_path: str = "",
    display_name: str = "",
) -> str:
    """Classify a BIM object by its property set, system path, and display name.

    This is a 1:1 Python port of
    ``DXTnavis.Services.RefinedXlsxExporter.InferClass``.

    Parameters
    ----------
    properties
        Mapping of ``"Category|PropertyName" → value`` strings for the object.
        Values may have a ``DisplayString:`` prefix; the classifier handles it.
        Keys starting with ``__`` are treated as meta and ignored.
    sys_path
        The object's System Path string (e.g. ``"TRAINING\\A2\\U04\\Equipment"``).
    display_name
        The object's display name (e.g. ``"Pipe-1-0042"``).

    Returns
    -------
    str
        One of: ``Piping``, ``Equipment``, ``Structure``, ``Electrical``,
        ``HVAC``, ``Instrumentation``, or any explicit class value found in a
        ``Class`` / ``ClassDisplayName`` property. Defaults to ``"Other"``.
    """
    # ---- Tier 1: explicit Class property ----
    for key, value in properties.items():
        if key.startswith("__"):
            continue
        prop_name = _split_property_name(key)
        if prop_name.lower() in ("classdisplayname", "class"):
            cleaned = clean_display_string(value)
            if cleaned:
                return cleaned

    # ---- Tier 2: property key inference ----
    has_pipeline = False
    has_equipment = False
    for key in properties.keys():
        if key.startswith("__"):
            continue
        lk = key.lower()
        if "pipeline" in lk or "piperun" in lk or "piping" in lk:
            has_pipeline = True
        if "equipment" in lk or "eqp type" in lk:
            has_equipment = True

    if has_pipeline:
        return "Piping"
    if has_equipment:
        return "Equipment"

    # ---- Tier 3: substring keyword matching ----
    # The C# code concatenates sys_path + " " + display_name + " " + every
    # property key, then lowercases the whole string and runs substring checks.
    parts: list[str] = [sys_path or "", display_name or ""]
    for key in properties.keys():
        if key.startswith("__"):
            continue
        parts.append(key)
    combined = " ".join(parts).lower()

    if any(kw in combined for kw in PIPING_KEYWORDS):
        return "Piping"
    if any(kw in combined for kw in EQUIPMENT_KEYWORDS):
        return "Equipment"
    if any(kw in combined for kw in STRUCTURE_KEYWORDS):
        return "Structure"
    if any(kw in combined for kw in ELECTRICAL_KEYWORDS):
        return "Electrical"
    if any(kw in combined for kw in HVAC_KEYWORDS):
        return "HVAC"
    if any(kw in combined for kw in INSTRUMENTATION_KEYWORDS):
        return "Instrumentation"

    return "Other"
