#!/usr/bin/env python3
"""Minimal FBX binary parser demo for the DXTnavis PR.

Walks ``gap_fallback.fbx`` and reports how many ``Model::Mesh`` entries
carry an SP3D ObjectId under the Korean-localized property key
``항목 - GUID``. Intended as reproducible evidence for the upstream PR.

Usage::

    python fbx_parser_demo.py path/to/gap_fallback.fbx

Notes:
    * Standard library only — no fbx-sdk, no Blender, no Assimp.
    * Supports FBX binary format (magic ``Kaydara FBX Binary``) version >= 7500.
    * Not a general-purpose FBX parser; only extracts the fields needed
      to demonstrate the locale / sidecar / coverage issues in the PR.
"""

from __future__ import annotations

import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"
GUID_PROPERTY_KEY = "항목 - GUID"  # Korean localized — this is the whole point of the PR.


@dataclass
class Node:
    name: str
    properties: list[Any] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)


_SCALAR = {"Y": ("<h", 2), "C": ("<?", 1), "I": ("<i", 4), "F": ("<f", 4),
           "D": ("<d", 8), "L": ("<q", 8)}


def _read_primitive(buf: memoryview, offset: int, type_code: bytes) -> tuple[Any, int]:
    tc = type_code.decode("ascii")
    if tc in _SCALAR:
        fmt, size = _SCALAR[tc]
        return struct.unpack_from(fmt, buf, offset)[0], offset + size
    if tc in {"f", "d", "l", "i", "b"}:  # array — payload only; we don't decode.
        _arr_len, enc, comp_len = struct.unpack_from("<III", buf, offset)
        payload = bytes(buf[offset + 12 : offset + 12 + comp_len])
        if enc == 1:
            payload = zlib.decompress(payload)
        return payload, offset + 12 + comp_len
    if tc in {"S", "R"}:  # string or raw bytes
        length = struct.unpack_from("<I", buf, offset)[0]
        raw = bytes(buf[offset + 4 : offset + 4 + length])
        offset += 4 + length
        if tc == "S":  # \x00\x01 is the FBX name/namespace separator
            return raw.replace(b"\x00\x01", b"::").decode("utf-8", errors="replace"), offset
        return raw, offset
    raise ValueError(f"unsupported FBX type code {tc!r} at offset {offset}")


def _read_node(buf: memoryview, offset: int, version: int) -> tuple[Node | None, int]:
    v75 = version >= 7500
    fmt = "<QQQ" if v75 else "<III"
    hdr = 25 if v75 else 13
    end_offset, num_props, _prop_list_len = struct.unpack_from(fmt, buf, offset)
    offset += hdr - 1  # leave 1 byte for name_len below
    name_len = struct.unpack_from("<B", buf, offset)[0]
    offset += 1

    if end_offset == 0:  # null record — terminates a sibling list
        return None, offset

    name = bytes(buf[offset : offset + name_len]).decode("utf-8", errors="replace")
    offset += name_len

    props: list[Any] = []
    for _ in range(num_props):
        type_code = bytes(buf[offset : offset + 1])
        offset += 1
        value, offset = _read_primitive(buf, offset, type_code)
        props.append(value)

    node = Node(name=name, properties=props)
    while offset < end_offset:
        child, offset = _read_node(buf, offset, version)
        if child is None:
            break
        node.children.append(child)
    return node, end_offset


def parse_fbx(path: Path) -> Node:
    data = path.read_bytes()
    if not data.startswith(MAGIC):
        raise ValueError(f"{path} is not an FBX binary file")
    version = struct.unpack_from("<I", data, len(MAGIC))[0]
    buf = memoryview(data)
    offset = len(MAGIC) + 4

    root = Node(name="__root__")
    while offset < len(data):
        child, new_offset = _read_node(buf, offset, version)
        if child is None:
            offset = new_offset
            break
        root.children.append(child)
        offset = new_offset
        if child.name == "" and not child.children:
            break
    return root


def iter_mesh_models(root: Node):
    objects = next((c for c in root.children if c.name == "Objects"), None)
    if objects is None:
        return
    for node in objects.children:
        if node.name != "Model":
            continue
        # Properties: [uid:int64, "Name::Model", "Mesh"]
        if len(node.properties) >= 3 and node.properties[2] == "Mesh":
            yield node


def extract_properties70(model: Node) -> dict[str, str]:
    props70 = next((c for c in model.children if c.name == "Properties70"), None)
    out: dict[str, str] = {}
    if props70 is None:
        return out
    for p in props70.children:
        if p.name != "P" or len(p.properties) < 5:
            continue
        key = p.properties[0]
        value = p.properties[4]
        if isinstance(key, str) and isinstance(value, str):
            out[key] = value
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} path/to/gap_fallback.fbx", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"file not found: {path}", file=sys.stderr)
        return 1

    root = parse_fbx(path)
    meshes = list(iter_mesh_models(root))

    total = len(meshes)
    with_guid: list[tuple[int, str, str]] = []
    geometry_missing: list[tuple[int, str]] = []
    other_missing: list[tuple[int, str, list[str]]] = []

    for idx, model in enumerate(meshes):
        name = model.properties[1] if len(model.properties) >= 2 else ""
        display = name.split("::")[-1] if isinstance(name, str) else ""
        p70 = extract_properties70(model)
        guid = p70.get(GUID_PROPERTY_KEY, "")
        if guid:
            with_guid.append((idx, display, guid))
        elif display == "Geometry":
            geometry_missing.append((idx, display))
        else:
            other_missing.append((idx, display, sorted(p70.keys())))

    pct = lambda n: f"{n/total:.1%}" if total else "n/a"
    print(f"FBX file: {path}")
    print(f"Total Model::Mesh entries: {total}")
    print(f"Extracted {len(with_guid)}/{total} GUIDs via Properties70['{GUID_PROPERTY_KEY}']\n")
    print("Category breakdown:")
    print(f"  [1] with GUID                : {len(with_guid):>4} ({pct(len(with_guid))})")
    print(f"  [2] no GUID, name='Geometry' : {len(geometry_missing):>4} ({pct(len(geometry_missing))})")
    print(f"  [3] no GUID, other           : {len(other_missing):>4} ({pct(len(other_missing))})\n")

    if with_guid:
        print("Sample [1] with GUID (first 3):")
        for idx, display, guid in with_guid[:3]:
            print(f"  mesh_index={idx:>4}  name={display!r:<40}  guid={guid}")
    if geometry_missing:
        print("\nSample [2] missing GUID (first 3):")
        for idx, display in geometry_missing[:3]:
            print(f"  mesh_index={idx:>4}  name={display!r}")
    if other_missing:
        print("\nSample [3] other missing (first 3, with property keys present):")
        for idx, display, keys in other_missing[:3]:
            print(f"  mesh_index={idx:>4}  name={display!r}  keys={keys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
