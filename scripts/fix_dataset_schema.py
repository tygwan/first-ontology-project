"""Fix broken parquet schema by rolling back D-AIFDE-7 timestamp cast.

Problem (M5 finding):
  D-AIFDE-7 used palantir-sdk write_pandas to cast String → datetime.
  write_pandas wrote Parquet as DATE logical (INT64 physical), causing
  Spark SchemaColumnConvertNotSupportedException.

Solution:
  Revert all `ingested_at_utc` columns to String (ISO format) and
  re-upload via palantir-sdk. String path is known-working.

Scope:
  - 6 Object Type datasets: local parquet already String → direct upload
  - 2 aggregate datasets: local parquet has datetime → convert to String, upload

Result:
  All 8 datasets have ingested_at_utc as String, Spark reads work again.
  Trade-off: lose time-series query capability (wasn't actively used).

Usage:
    export FOUNDRY_TOKEN=...
    python scripts/fix_dataset_schema.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

pd.set_option("future.infer_string", False)

from palantir.core.config import StaticHostnameProvider, StaticTokenProvider
from palantir.datasets.client import (
    PalantirContext, DatasetServices, DatasetsClient, DatasetLocator
)
from palantir.datasets.core import Dataset

from foundry_sdk import FoundryClient, UserTokenAuth

HOSTNAME = "datayoon.usw-18.palantirfoundry.com"
PROJECT = "/Datayoon-09825c/BIM-KG"

DATASETS = [
    ("bim_piping",       "data/ontology/2026-04-12/object_types/piping.parquet"),
    ("bim_structural",   "data/ontology/2026-04-12/object_types/structural.parquet"),
    ("bim_equipment",    "data/ontology/2026-04-12/object_types/equipment.parquet"),
    ("bim_electrical",   "data/ontology/2026-04-12/object_types/electrical.parquet"),
    ("bim_hvac",         "data/ontology/2026-04-12/object_types/hvac.parquet"),
    ("bim_other",        "data/ontology/2026-04-12/object_types/other.parquet"),
    ("bim_pipelines",    "data/ontology/2026-04-12/bim_pipelines.parquet"),
    ("bim_piperuns",     "data/ontology/2026-04-12/bim_piperuns.parquet"),
]


def fix_dtypes_for_foundry(df: pd.DataFrame) -> pd.DataFrame:
    """palantir-sdk compatibility fixes."""
    for col in df.columns:
        dt = str(df[col].dtype)
        # CRITICAL: 모든 datetime 을 ISO String 으로 변환
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


def main():
    token = os.environ.get("FOUNDRY_TOKEN")
    if not token:
        sys.exit("FOUNDRY_TOKEN env var required")

    # Both SDKs
    fd_client = FoundryClient(auth=UserTokenAuth(token=token), hostname=HOSTNAME)
    hp = StaticHostnameProvider(HOSTNAME)
    tp = StaticTokenProvider(token)
    legacy = DatasetsClient(
        DatasetServices(PalantirContext(hostname=hp, auth=tp))
    )

    print(f"Re-uploading 8 datasets with String ingested_at_utc (rollback D-AIFDE-7)\n")

    rid_cache = {}
    for ds_name, local_path in DATASETS:
        print(f"=== {ds_name} ===")
        local = Path(local_path)
        if not local.exists():
            print(f"  ⚠️ local not found: {local_path}")
            continue

        # Resolve RID
        try:
            res = fd_client.filesystem.Resource.get_by_path(
                path=f"{PROJECT}/{ds_name}", preview=True
            )
            rid = res.rid
            rid_cache[ds_name] = rid
        except Exception as e:
            print(f"  ❌ RID: {e}")
            continue

        # Read local, check dtype, fix all
        df = pd.read_parquet(local)
        orig_ts_dtype = str(df.get('ingested_at_utc', pd.Series()).dtype) if 'ingested_at_utc' in df.columns else "N/A"
        print(f"  local: {len(df):,} × {len(df.columns)} (ingested_at_utc: {orig_ts_dtype})")

        df = fix_dtypes_for_foundry(df)

        # 확인: ingested_at_utc 가 문자열 인지
        if 'ingested_at_utc' in df.columns:
            sample = df['ingested_at_utc'].iloc[0]
            print(f"  after fix: '{sample}' ({type(sample).__name__})")

        # Upload via legacy SDK write_pandas
        try:
            ds = Dataset(legacy, DatasetLocator(rid, "master"))
            ds.write_pandas(df)
            print(f"  ✓ uploaded")
        except Exception as e:
            print(f"  ❌ UPLOAD: {type(e).__name__}: {str(e)[:200]}")

    # Verification via foundry-sdk read_table
    print(f"\n\n=== Verification ===")
    import time
    time.sleep(5)
    for ds_name, _ in DATASETS:
        rid = rid_cache.get(ds_name)
        if not rid:
            continue
        try:
            response = fd_client.datasets.Dataset.read_table(rid, format="ARROW")
            table = response.arrow()
            n_rows = table.num_rows
            ts_field = table.schema.field('ingested_at_utc') if 'ingested_at_utc' in table.schema.names else None
            ts_type = ts_field.type if ts_field else "N/A"
            print(f"  {ds_name:<25s}  rows={n_rows:>6,}  ingested_at_utc → {ts_type}  ✓")
        except Exception as e:
            print(f"  {ds_name:<25s}  ❌ {type(e).__name__}: {str(e)[:80]}")


if __name__ == "__main__":
    main()
