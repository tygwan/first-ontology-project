"""FBX 내부 788 mesh를 개별 GLB로 export.

gap_fallback.fbx의 각 Mesh Model을 추출해서 mesh/{object_id}.glb로 저장.

좌표 변환: Gold(x, y, z) = FBX(-x, z, y)
- FBX: Z-up + X 미러 (SP3D C# 관례)
- Gold: Y-up 오른손 좌표계 (glTF 표준)

매핑: temp/fbx_mesh_mapping_final.parquet (mesh_index ↔ object_id)
  - 740개: Properties70 "항목 - GUID" 기반 exact 매칭
  - 48개:  centroid Hungarian assignment (좌표 변환 후)

Usage:
    python scripts/export_fbx_meshes_to_glb.py [--output mesh/] [--dry-run]
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import assimp_py
import numpy as np
import pandas as pd
import pygltflib
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Primitive, Mesh, Node, Scene, Asset


FBX_PATH = Path(
    "data/backup/260415 최신 glb/dxtnavis_export_20260415_044932/gap_fallback.fbx"
)
MAPPING_PATH = Path("temp/fbx_mesh_mapping_final.parquet")
DEFAULT_OUTPUT = Path("data/raw/dxtnavis/2026-04-12/mesh")

#: Coordinate transform matrix: Gold(x, y, z) = FBX(-x, z, y)
#: Applied to vertices and normals (normals without translation).
#: In glTF, Y is up; we rotate FBX's Z-up to Y-up and flip X-axis mirror.
GOLD_FROM_FBX = np.array([
    [-1, 0, 0, 0],
    [ 0, 0, 1, 0],
    [ 0, 1, 0, 0],
    [ 0, 0, 0, 1],
], dtype=np.float64)


def walk_with_transform(node, parent_transform=None, result=None):
    """씬 그래프 순회하며 world transform 누적."""
    if result is None:
        result = {}
    if parent_transform is None:
        parent_transform = np.eye(4, dtype=np.float64)
    local = np.array(node.transformation, dtype=np.float64).reshape(4, 4)
    world = parent_transform @ local
    for mesh_idx in node.mesh_indices:
        result[mesh_idx] = world
    for child in node.children:
        walk_with_transform(child, world, result)
    return result


def apply_transform_to_vertices(vertices: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """(N, 3) vertices에 4x4 행렬 적용."""
    homogeneous = np.hstack([vertices, np.ones((len(vertices), 1))])
    transformed = (matrix @ homogeneous.T).T
    return transformed[:, :3].astype(np.float32)


def apply_transform_to_normals(normals: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """(N, 3) normals에 3x3 rotation 부분만 적용 (translation 제외)."""
    rotation = matrix[:3, :3]
    # For non-uniform scaling we'd need inverse-transpose; for our pure rotation/mirror this works
    transformed = (rotation @ normals.T).T
    # Re-normalize
    norms = np.linalg.norm(transformed, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (transformed / norms).astype(np.float32)


def mesh_to_glb_bytes(vertices: np.ndarray, indices: np.ndarray,
                      normals: np.ndarray | None = None) -> bytes:
    """단일 mesh를 GLB 바이너리로 변환."""
    vertices = vertices.astype(np.float32)
    indices = indices.astype(np.uint32)

    # Buffer 구성: vertices + (normals) + indices
    vert_bytes = vertices.tobytes()
    idx_bytes = indices.tobytes()
    norm_bytes = normals.tobytes() if normals is not None else b""

    # glTF는 4-byte alignment 필요
    def pad(data: bytes) -> bytes:
        rem = len(data) % 4
        return data + b"\x00" * ((4 - rem) if rem else 0)

    vert_bytes_padded = pad(vert_bytes)
    norm_bytes_padded = pad(norm_bytes) if norm_bytes else b""
    idx_bytes_padded = pad(idx_bytes)

    buffer_data = vert_bytes_padded + norm_bytes_padded + idx_bytes_padded

    buffer_views = [
        BufferView(buffer=0, byteOffset=0,
                   byteLength=len(vert_bytes), target=pygltflib.ARRAY_BUFFER),
    ]
    accessors = [
        Accessor(bufferView=0, componentType=pygltflib.FLOAT, count=len(vertices),
                 type="VEC3",
                 min=vertices.min(axis=0).tolist(),
                 max=vertices.max(axis=0).tolist()),
    ]
    primitive_attrs = {"POSITION": 0}
    offset = len(vert_bytes_padded)

    if normals is not None:
        buffer_views.append(BufferView(
            buffer=0, byteOffset=offset,
            byteLength=len(norm_bytes), target=pygltflib.ARRAY_BUFFER
        ))
        accessors.append(Accessor(
            bufferView=len(buffer_views) - 1,
            componentType=pygltflib.FLOAT,
            count=len(normals), type="VEC3"
        ))
        primitive_attrs["NORMAL"] = len(accessors) - 1
        offset += len(norm_bytes_padded)

    # Indices
    buffer_views.append(BufferView(
        buffer=0, byteOffset=offset,
        byteLength=len(idx_bytes),
        target=pygltflib.ELEMENT_ARRAY_BUFFER
    ))
    accessors.append(Accessor(
        bufferView=len(buffer_views) - 1,
        componentType=pygltflib.UNSIGNED_INT,
        count=len(indices), type="SCALAR"
    ))
    indices_accessor_idx = len(accessors) - 1

    gltf = GLTF2(
        asset=Asset(version="2.0", generator="bimkg fbx→glb exporter"),
        scenes=[Scene(nodes=[0])],
        scene=0,
        nodes=[Node(mesh=0)],
        meshes=[Mesh(primitives=[Primitive(
            attributes=primitive_attrs,
            indices=indices_accessor_idx,
            mode=pygltflib.TRIANGLES,
        )])],
        accessors=accessors,
        bufferViews=buffer_views,
        buffers=[Buffer(byteLength=len(buffer_data))],
    )
    gltf.set_binary_blob(buffer_data)
    return b"".join(gltf.save_to_bytes())


def extract_mesh_data(mesh, world_transform):
    """Assimp 메시에서 vertices/indices/normals 추출 + 좌표 변환 적용."""
    verts = np.array(list(mesh.vertices), dtype=np.float64).reshape(-1, 3)

    # World transform 적용 (scene graph 계층)
    verts_world = apply_transform_to_vertices(verts, world_transform).astype(np.float64)

    # FBX → Gold 좌표계 변환
    verts_gold = apply_transform_to_vertices(verts_world, GOLD_FROM_FBX)

    # Indices: assimp가 num_faces * 3 개의 UNSIGNED_INT index 제공
    indices_raw = np.array(list(mesh.indices), dtype=np.uint32)

    # Normals
    normals_gold = None
    if mesh.normals is not None:
        try:
            norms = np.array(list(mesh.normals), dtype=np.float64).reshape(-1, 3)
            norms_world = apply_transform_to_normals(norms, world_transform[:3, :3]).astype(np.float64)
            normals_gold = apply_transform_to_normals(norms_world, GOLD_FROM_FBX[:3, :3])
        except Exception:
            pass

    return verts_gold, indices_raw, normals_gold


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="GLB 저장 디렉토리 (default: data/raw/dxtnavis/2026-04-12/mesh)")
    parser.add_argument("--dry-run", action="store_true",
                        help="매핑/추출만 검증, 파일 쓰지 않음")
    parser.add_argument("--limit", type=int, default=None,
                        help="처음 N개만 (디버그용)")
    args = parser.parse_args()

    # 매핑 로드
    if not MAPPING_PATH.exists():
        raise SystemExit(f"매핑 파일 없음: {MAPPING_PATH}")
    mapping = pd.read_parquet(MAPPING_PATH)
    print(f"매핑 로드: {len(mapping)} rows")

    # FBX 로드
    print(f"FBX 로드: {FBX_PATH}")
    scene = assimp_py.import_file(str(FBX_PATH), assimp_py.Process_Triangulate)
    print(f"  → {len(scene.meshes)} meshes")

    # 각 mesh의 world transform 계산
    transforms = walk_with_transform(scene.root_node)
    print(f"  → {len(transforms)} mesh-bearing nodes")

    # 출력 디렉토리
    if not args.dry_run:
        args.output.mkdir(parents=True, exist_ok=True)
        print(f"출력: {args.output}")

    # 처리
    results = {"ok": 0, "skip_no_transform": 0, "skip_no_mapping": 0, "fail": 0}

    mesh_to_oid = dict(zip(mapping['mesh_index'].astype(int), mapping['object_id']))

    items = list(enumerate(scene.meshes))
    if args.limit:
        items = items[:args.limit]

    for idx, mesh in items:
        oid = mesh_to_oid.get(idx)
        if not oid:
            results["skip_no_mapping"] += 1
            continue

        world_tf = transforms.get(idx)
        if world_tf is None:
            # Fallback: identity (mesh가 어느 노드에도 바인딩 안 된 경우)
            world_tf = np.eye(4)
            results["skip_no_transform"] += 1

        try:
            verts, indices, normals = extract_mesh_data(mesh, world_tf)
            glb_bytes = mesh_to_glb_bytes(verts, indices, normals)

            out_path = args.output / f"{oid}.glb"
            if not args.dry_run:
                out_path.write_bytes(glb_bytes)

            results["ok"] += 1
            if results["ok"] % 100 == 0:
                print(f"  {results['ok']}/{len(items)}...")

        except Exception as e:
            results["fail"] += 1
            print(f"  FAIL mesh_idx={idx} oid={oid}: {type(e).__name__}: {e}")

    print(f"\n=== 완료 ===")
    for k, v in results.items():
        print(f"  {k}: {v}")

    if not args.dry_run:
        written = list(args.output.glob("*.glb"))
        # Only count NEW ones (fbx-supplied)
        new_glbs = set(mapping['object_id']) & {p.stem for p in written}
        print(f"\n출력 디렉토리 총 GLB: {len(written):,}")
        print(f"  이번 세션에 추가된 GLB: {len(new_glbs):,}")


if __name__ == "__main__":
    main()
