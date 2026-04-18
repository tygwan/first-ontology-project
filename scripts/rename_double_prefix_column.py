"""[ONE-TIME SCRIPT — ALREADY EXECUTED 2026-04-17]

Rename `sp3d_sp3d_moniker` → `sp3d_moniker` across all 6 Object Type datasets.

⚠️ DO NOT RE-RUN. 이미 D-AIFDE-20 결정에 따라 6개 parquet + Foundry
   업로드 모두 적용 완료. 재실행 시 no-op (source col 이 더 이상 존재 안함).

기록 목적으로 git 에 보존. DXTnavis upstream PR 로 이중 prefix 가 원본에서
해소되면 이 파일은 삭제 가능.


Root cause (upstream):
  DXTnavis XLSX column loader adds `sp3d_` prefix to SP3D property
  names. The source "SP3d Moniker" became `sp3d_sp3d_moniker`
  (double prefix). This breaks auto-mapping in Foundry Ontology
  Manager (camelCase conversion of `sp3d_moniker` = `sp3dMoniker`,
  which matches HasSP3DMetadata.sp3dMoniker interface property, but
  the actual column is `sp3d_sp3d_moniker`).

Fix:
  Rename column in-place (parquet) for 6 Object Type datasets,
  then re-upload via foundry-sdk File API.

After this fix:
  - Auto-mapping works for sp3dMoniker → sp3d_moniker
  - Manual "Choose existing" step no longer needed per Object Type
  - Existing BimPiping property mapping (sp3dMoniker → sp3d_sp3d_moniker)
    needs UI update to point at sp3d_moniker

Governance:
  Another raw-data modification (D-AIFDE-13 violation). Justified
  because it fixes a structural bug at source (upstream naming),
  not just a workaround. Alternative (Pipeline Builder view) would
  require rebuilding 6 transforms. Accept the violation and record
  as D-AIFDE-20 in Phase 2 session log.

Usage:
    export FOUNDRY_TOKEN=...
    python scripts/rename_double_prefix_column.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

pd.set_option("future.infer_string", False)

from foundry_sdk import FoundryClient, UserTokenAuth

HOSTNAME = "datayoon.usw-18.palantirfoundry.com"
PROJECT = "/Datayoon-09825c/BIM-KG"

DATASETS = [
    ("bim_piping",      "data/ontology/2026-04-12/object_types/piping.parquet"),
    ("bim_structural",  "data/ontology/2026-04-12/object_types/structural.parquet"),
    ("bim_equipment",   "data/ontology/2026-04-12/object_types/equipment.parquet"),
    ("bim_electrical",  "data/ontology/2026-04-12/object_types/electrical.parquet"),
    ("bim_hvac",        "data/ontology/2026-04-12/object_types/hvac.parquet"),
    ("bim_other",       "data/ontology/2026-04-12/object_types/other.parquet"),
]

SOURCE_COL = "sp3d_sp3d_moniker"
TARGET_COL = "sp3d_moniker"


def main():
    token = os.environ.get("FOUNDRY_TOKEN")
    if not token:
        sys.exit("FOUNDRY_TOKEN env var required")

    client = FoundryClient(auth=UserTokenAuth(token=token), hostname=HOSTNAME)

    # Step 1: Rename local parquet files
    print(f"=== Step 1: Rename local parquet column ({SOURCE_COL} → {TARGET_COL}) ===\n")
    for ds_name, path in DATASETS:
        p = Path(path)
        if not p.exists():
            print(f"  ⚠️ {ds_name}: local not found")
            continue

        df = pd.read_parquet(p)
        if SOURCE_COL not in df.columns:
            print(f"  {ds_name:<20s}  (no {SOURCE_COL} column, skipping)")
            continue
        if TARGET_COL in df.columns:
            print(f"  {ds_name:<20s}  ⚠️ COLLISION: {TARGET_COL} already exists, skipping")
            continue

        df = df.rename(columns={SOURCE_COL: TARGET_COL})
        # 로컬 parquet overwrite (같은 경로)
        df.to_parquet(p, index=False)
        print(f"  {ds_name:<20s}  ✓ renamed, saved ({len(df):,} rows)")

    # Step 2: Re-upload to Foundry
    print(f"\n=== Step 2: Re-upload to Foundry (via SNAPSHOT transactions) ===\n")
    rid_cache = {}
    for ds_name, path in DATASETS:
        p = Path(path)
        if not p.exists():
            continue

        try:
            res = client.filesystem.Resource.get_by_path(
                path=f"{PROJECT}/{ds_name}", preview=True
            )
            rid = res.rid
            rid_cache[ds_name] = rid
        except Exception as e:
            print(f"  ❌ {ds_name}: RID lookup failed: {e}")
            continue

        body = p.read_bytes()
        size_mb = len(body) / 1024 / 1024

        try:
            txn = client.datasets.Dataset.Transaction.create(
                rid, transaction_type="SNAPSHOT"
            )
            client.datasets.Dataset.File.upload(
                rid, file_path=f"{ds_name}.parquet",
                body=body, transaction_rid=txn.rid,
            )
            client.datasets.Dataset.Transaction.commit(rid, txn.rid)
            print(f"  {ds_name:<20s}  ✓ uploaded ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"  ❌ {ds_name}: {type(e).__name__}: {str(e)[:150]}")

    # Step 3: Schema registration (Foundry needs this after File.upload)
    print(f"\n=== Step 3: Register schema (via palantir-sdk write_pandas pass) ===\n")
    # palantir-sdk 를 다시 사용해서 schema 등록 (write_pandas 가 이 역할 수행)
    from palantir.core.config import StaticHostnameProvider, StaticTokenProvider
    from palantir.datasets.client import (
        PalantirContext, DatasetServices, DatasetsClient, DatasetLocator
    )
    from palantir.datasets.core import Dataset

    hp = StaticHostnameProvider(HOSTNAME)
    tp = StaticTokenProvider(token)
    legacy = DatasetsClient(
        DatasetServices(PalantirContext(hostname=hp, auth=tp))
    )

    def fix_dtypes(df):
        for col in df.columns:
            dt = str(df[col].dtype)
            if "datetime" in dt.lower() or "date" in dt.lower():
                df[col] = df[col].astype(str).replace("NaT", "")
            elif dt == "Int64":
                df[col] = df[col].astype("float64")
            elif df[col].dtype == object:
                if df[col].isna().all():
                    df[col] = ""
                else:
                    df[col] = df[col].fillna("")
        return df

    for ds_name, path in DATASETS:
        rid = rid_cache.get(ds_name)
        if not rid:
            continue
        df = pd.read_parquet(path)
        df = fix_dtypes(df)
        try:
            ds = Dataset(legacy, DatasetLocator(rid, "master"))
            ds.write_pandas(df)
            print(f"  {ds_name:<20s}  ✓ schema registered")
        except Exception as e:
            print(f"  ❌ {ds_name}: {str(e)[:150]}")

    # Step 4: Verify
    print(f"\n=== Step 4: Verify column rename in Foundry ===\n")
    time.sleep(3)
    for ds_name, _ in DATASETS:
        rid = rid_cache.get(ds_name)
        if not rid:
            continue
        try:
            response = client.datasets.Dataset.read_table(rid, format="ARROW")
            table = response.to_pandas()
            has_target = TARGET_COL in table.columns
            has_source = SOURCE_COL in table.columns
            status = "✓" if (has_target and not has_source) else "⚠️"
            print(f"  {ds_name:<20s}  {TARGET_COL}:{'있음' if has_target else '없음'}  {SOURCE_COL}:{'있음' if has_source else '없음'}  {status}")
        except Exception as e:
            print(f"  {ds_name:<20s}  ❌ read: {str(e)[:80]}")


if __name__ == "__main__":
    main()
