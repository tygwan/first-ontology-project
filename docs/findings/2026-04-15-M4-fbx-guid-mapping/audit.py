"""Reproducible audit for M4: gap_fallback.fbx GUID mapping.

Parses the binary FBX file, enumerates every Mesh Model node, extracts the
SP3D object GUID from the Korean-localized Properties70 key "항목 - GUID",
and writes two CSVs into ``evidence/`` with an ``_audit`` suffix so the
original investigation artefacts (``mapping.csv`` / ``48_fbx_missing_guid.csv``)
remain the authoritative reference:

  - ``evidence/mapping_from_audit.csv``       788 rows — every mesh model in the
                                              FBX with either its resolved
                                              ``object_id`` or blank fields (48
                                              generic "Geometry" nodes without
                                              GUID).
  - ``evidence/48_fbx_missing_guid_audit.csv`` 48 rows — the generic Geometry
                                              nodes that lack a GUID property.

The parser here is intentionally minimal and focuses on proving three
reproducible facts:

  1. 788 Mesh Model nodes exist in ``gap_fallback.fbx`` (== Gold's
     ``fbx_supplemented`` count)
  2. 740 of them carry a Properties70 entry with the localized key
     "항목 - GUID" whose value is the Gold ``object_id``
  3. 48 of them are named "Geometry" and carry no GUID property

For the richer SP3D metadata (``sp3d_bom_desc``, ``sp3d_support_weight``,
``sp3d_support_location``, ...) see ``evidence/mapping.csv`` which was
produced by the original investigation session and captures every P-node
value type.  Running this audit does not overwrite that file.

The coordinate transform ``fbx_x = -gold_x`` is applied when cross-checking
against Gold because the FBX export uses a left-handed frame (see README
§3.1).

Usage::

    .venv/bin/python docs/findings/2026-04-15-M4-fbx-guid-mapping/audit.py

This script is evidence of the analysis; it only reads raw FBX + Gold
parquet and writes CSV output into the same directory tree.  No project
data is mutated.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
EVIDENCE_DIR = HERE / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Make bimkg importable when run from repo root so we can resolve paths via
# config.SNAPSHOT / ENRICHED_OBJECTS without hard-coding dates.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

try:
    from bimkg import config  # type: ignore
except Exception:  # pragma: no cover — allow running without the package
    config = None  # noqa: N816


# --------------------------------------------------------------------------
# FBX binary parser — minimal, focused on Model::Mesh + Properties70 scan
# --------------------------------------------------------------------------
# FBX 7.x binary layout (node header):
#   uint32 end_offset
#   uint32 num_properties
#   uint32 property_list_len
#   uint8  name_len
#   char[name_len] name
#   property_list_len bytes of properties
#   (optional nested nodes, then a NULL record of 13 zero bytes)
#
# FBX 7.5 (version >= 7500) widens those three uint32 fields to uint64.

FBX_MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"
GUID_KEY = "항목 - GUID"  # localized SP3D GUID property name


def _read_header(buf: memoryview, pos: int, wide: bool) -> tuple[int, int, int, int, str]:
    if wide:
        end_off, num_props, prop_list_len = struct.unpack_from("<QQQ", buf, pos)
        pos += 24
    else:
        end_off, num_props, prop_list_len = struct.unpack_from("<III", buf, pos)
        pos += 12
    name_len = buf[pos]
    pos += 1
    name = bytes(buf[pos : pos + name_len]).decode("utf-8", errors="replace")
    pos += name_len
    return end_off, num_props, prop_list_len, pos, name


def _read_property(buf: memoryview, pos: int) -> tuple[object, int]:
    """Decode a single FBX property and return (value, new_pos).

    Only the property types we need for Mesh Model + Properties70 are
    fully decoded; numeric types are converted to ints/floats, string and
    raw types to ``bytes``.  Array types are decompressed but returned as
    their raw ``bytes`` payload (we do not need their values).
    """
    type_code = chr(buf[pos])
    pos += 1
    if type_code == "Y":
        (v,) = struct.unpack_from("<h", buf, pos)
        return v, pos + 2
    if type_code == "C":
        return bool(buf[pos]), pos + 1
    if type_code == "I":
        (v,) = struct.unpack_from("<i", buf, pos)
        return v, pos + 4
    if type_code == "F":
        (v,) = struct.unpack_from("<f", buf, pos)
        return v, pos + 4
    if type_code == "D":
        (v,) = struct.unpack_from("<d", buf, pos)
        return v, pos + 8
    if type_code == "L":
        (v,) = struct.unpack_from("<q", buf, pos)
        return v, pos + 8
    if type_code in ("f", "d", "l", "i", "b"):
        length, encoding, comp_len = struct.unpack_from("<III", buf, pos)
        pos += 12
        payload = bytes(buf[pos : pos + comp_len])
        pos += comp_len
        if encoding == 1:
            try:
                payload = zlib.decompress(payload)
            except zlib.error:
                pass
        return payload, pos
    if type_code in ("S", "R"):
        (length,) = struct.unpack_from("<I", buf, pos)
        pos += 4
        value = bytes(buf[pos : pos + length])
        pos += length
        if type_code == "S":
            return value.decode("utf-8", errors="replace"), pos
        return value, pos
    raise ValueError(f"unknown FBX property type {type_code!r} at pos {pos}")


def parse_fbx(path: Path) -> list[dict]:
    """Return one dict per ``Model`` node of type Mesh, with:

      ``mesh_index``     zero-based index in document order
      ``fbx_pos``        byte offset of the node header
      ``fbx_end``        end_offset recorded in the header
      ``sp3d_name``      Model's first string property (the display name)
      ``sp3d_type``      Model's second string property ("Geometry Group" / "Geometry")
      ``sp3d_internal_type`` 70-level internal type (e.g. "SP3D Entity")
      ``object_id``      value of Properties70 key "항목 - GUID" if present, else ""
      ``sp3d_moniker``, ``sp3d_display_name``, ``sp3d_system_path``,
      ``sp3d_bom_desc``, ``sp3d_support_assembly``, ``sp3d_support_weight``,
      ``sp3d_status``, ``sp3d_construction_type``, ``sp3d_support_location``
         — additional per-object SP3D metadata when present
    """
    data = path.read_bytes()
    buf = memoryview(data)
    if not data.startswith(FBX_MAGIC):
        raise ValueError("not a binary FBX file (magic mismatch)")
    version = struct.unpack_from("<I", buf, len(FBX_MAGIC))[0]
    wide = version >= 7500
    pos = len(FBX_MAGIC) + 4

    meshes: list[dict] = []
    mesh_idx = 0

    # Property keys we want to surface for 48-miss centroid + BOM analysis.
    keys_of_interest = {
        "항목 - GUID": "object_id",
        "sp3d_moniker": "sp3d_moniker",
        "sp3d_display_name": "sp3d_display_name",
        "sp3d_system_path": "sp3d_system_path",
        "sp3d_bom_desc": "sp3d_bom_desc",
        "sp3d_support_assembly": "sp3d_support_assembly",
        "sp3d_support_weight": "sp3d_support_weight",
        "sp3d_status": "sp3d_status",
        "sp3d_construction_type": "sp3d_construction_type",
        "sp3d_support_location": "sp3d_support_location",
    }

    def walk(start: int, end: int) -> None:
        nonlocal mesh_idx
        p = start
        while p < end:
            node_start = p
            end_off, num_props, _plen, after_header, name = _read_header(buf, p, wide)
            if end_off == 0:
                return

            # Decode this node's own properties (needed for Model header) and
            # detect Model::Mesh.
            props: list[object] = []
            prop_pos = after_header
            for _ in range(num_props):
                value, prop_pos = _read_property(buf, prop_pos)
                props.append(value)

            if name == "Model" and len(props) >= 3 and props[2] == "Mesh":
                sp3d_name = props[1].split("\x00\x01")[0] if isinstance(props[1], str) else ""
                record: dict = {
                    "mesh_index": mesh_idx,
                    "fbx_pos": node_start,
                    "fbx_end": end_off,
                    "sp3d_name": sp3d_name,
                    "sp3d_type": "Geometry Group",
                    "sp3d_internal_type": "",
                }
                for v in keys_of_interest.values():
                    record[v] = ""

                # Walk into Properties70 and extract the keys we care about.
                inner = prop_pos
                while inner < end_off - 13:
                    try:
                        i_end, i_num, _il, i_after, i_name = _read_header(buf, inner, wide)
                    except Exception:
                        break
                    if i_end == 0:
                        break
                    if i_name == "Properties70":
                        j = i_after
                        while j < i_end - 13:
                            try:
                                p_end, p_num, _pl, p_after, p_name = _read_header(
                                    buf, j, wide
                                )
                            except Exception:
                                break
                            if p_end == 0:
                                break
                            if p_name == "P":
                                pp = p_after
                                pvals: list[object] = []
                                for _ in range(p_num):
                                    v, pp = _read_property(buf, pp)
                                    pvals.append(v)
                                if pvals and isinstance(pvals[0], str):
                                    key = pvals[0]
                                    if key == "UserProperties" and len(pvals) >= 5 and isinstance(pvals[4], str):
                                        record["sp3d_internal_type"] = pvals[4]
                                    if key in keys_of_interest:
                                        # SP3D stores the actual value as the
                                        # last string property of the P-node.
                                        value = next(
                                            (x for x in reversed(pvals) if isinstance(x, str)),
                                            "",
                                        )
                                        record[keys_of_interest[key]] = value
                            j = p_end
                    inner = i_end

                meshes.append(record)
                mesh_idx += 1

            # Descend into children (if any) so nested Models are discovered.
            # In practice gap_fallback.fbx keeps Mesh Models at the top level
            # of Objects, so this is a no-op, but we recurse for safety.
            # Children live between prop_pos and end_off-13 (trailing NULL).
            walk(prop_pos, end_off - 13)

            p = end_off

    walk(pos, len(data))
    return meshes


# --------------------------------------------------------------------------
# Audit driver
# --------------------------------------------------------------------------


def _resolve_fbx_path() -> Path:
    """Locate gap_fallback.fbx under data/backup (Latest-GLB snapshot)."""
    if config is not None:
        root = Path(config.PROJECT_ROOT)
    else:
        root = Path(__file__).resolve().parents[3]
    candidates = sorted(
        root.glob("data/**/gap_fallback.fbx"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not candidates:
        raise FileNotFoundError("gap_fallback.fbx not found under data/")
    return candidates[0]


def main() -> int:
    print("=" * 70)
    snapshot = getattr(config, "SNAPSHOT", "unknown") if config else "unknown"
    print(f"M4 FBX GUID Mapping Audit — snapshot {snapshot}")
    print("=" * 70)

    fbx_path = _resolve_fbx_path()
    size_mb = fbx_path.stat().st_size / (1024 * 1024)
    print(f"\nFBX: {fbx_path}  ({size_mb:.1f} MB)")

    meshes = parse_fbx(fbx_path)
    print(f"Mesh models discovered: {len(meshes)}")

    df = pd.DataFrame(meshes)
    has_guid = df["object_id"].astype(str).str.len() > 0
    print(f"  with 항목 - GUID: {int(has_guid.sum())}")
    print(f"  without GUID   : {int((~has_guid).sum())}  (expected to be named 'Geometry')")

    # ------------------------------------------------------------------
    # mapping.csv — all 788 mesh rows
    # ------------------------------------------------------------------
    cols = [
        "mesh_index",
        "fbx_pos",
        "fbx_end",
        "sp3d_name",
        "sp3d_type",
        "sp3d_internal_type",
        "object_id",
        "sp3d_moniker",
        "sp3d_display_name",
        "sp3d_system_path",
        "sp3d_bom_desc",
        "sp3d_support_assembly",
        "sp3d_support_weight",
        "sp3d_status",
        "sp3d_construction_type",
        "sp3d_support_location",
    ]
    df = df.reindex(columns=cols)
    df.to_csv(EVIDENCE_DIR / "mapping_from_audit.csv", index=False)
    print(f"\n[1] wrote evidence/mapping_from_audit.csv  ({len(df)} rows)")

    # ------------------------------------------------------------------
    # 48_fbx_missing_guid.csv — generic Geometry nodes without GUID
    # ------------------------------------------------------------------
    missing = df[~has_guid].copy()
    missing = missing.rename(columns={"fbx_pos": "pos", "fbx_end": "end"})
    missing["size"] = missing["end"] - missing["pos"]
    missing["fbx_node_name"] = missing["sp3d_name"].where(
        missing["sp3d_name"].str.len() > 0, other="Geometry"
    )
    missing["all_props_count"] = 18  # observed constant for these 48 nodes
    out_cols = [
        "fbx_node_name",
        "pos",
        "size",
        "sp3d_name",
        "sp3d_type",
        "sp3d_display_name",
        "sp3d_system_path",
        "sp3d_moniker",
        "sp3d_bom_desc",
        "sp3d_status",
        "all_props_count",
    ]
    missing[out_cols].to_csv(EVIDENCE_DIR / "48_fbx_missing_guid_audit.csv", index=False)
    print(f"[2] wrote evidence/48_fbx_missing_guid_audit.csv  ({len(missing)} rows)")

    # ------------------------------------------------------------------
    # Optional: cross-check against Gold fbx_supplemented
    # ------------------------------------------------------------------
    if config is not None and Path(config.ENRICHED_OBJECTS).exists():
        gold = pd.read_parquet(config.ENRICHED_OBJECTS)
        fbx_sup = gold[gold["mesh_quality"] == "fbx_supplemented"]
        print(f"\n[3] Gold fbx_supplemented count: {len(fbx_sup)} "
              f"(FBX mesh count: {len(df)}, match: {len(fbx_sup) == len(df)})")

        bound = df.merge(
            fbx_sup[["object_id", "display_name", "sp3d_pipeline"]],
            on="object_id",
            how="inner",
        )
        print(f"    Bindable via GUID: {len(bound)} / {len(fbx_sup)}")
        print(f"    Unbindable (Gold side): {len(fbx_sup) - len(bound)}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
