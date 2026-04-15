"""Cast ingested_at_utc from String ISO to pandas datetime across all 6 Object Type datasets.

Phase 2 Ontology modeling decision: cast this column to Timestamp for
Foundry time-series queries.

Usage:
    export FOUNDRY_TOKEN=...
    python scripts/cast_timestamp_columns.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

pd.set_option("future.infer_string", False)

# Avoid polluting: palantir-sdk needs future.infer_string=False BEFORE import
from palantir.core.config import StaticHostnameProvider, StaticTokenProvider
from palantir.datasets.client import (
    PalantirContext, DatasetServices, DatasetsClient, DatasetLocator
)
from palantir.datasets.core import Dataset

from foundry_sdk import FoundryClient, UserTokenAuth

HOSTNAME = "datayoon.usw-18.palantirfoundry.com"
PROJECT = "/Datayoon-09825c/BIM-KG"

DATASETS = [
    "bim_piping", "bim_structural", "bim_equipment",
    "bim_electrical", "bim_hvac", "bim_other",
]

# Column to cast
TS_COL = "ingested_at_utc"


def fix_dtypes_for_foundry(df: pd.DataFrame) -> pd.DataFrame:
    """Palantir SDK dtype compatibility."""
    for col in df.columns:
        if col == TS_COL:
            # Keep as datetime
            continue
        dt = str(df[col].dtype)
        if dt == "Int64":
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

    # Connect (both SDKs)
    fd_client = FoundryClient(auth=UserTokenAuth(token=token), hostname=HOSTNAME)
    hp = StaticHostnameProvider(HOSTNAME)
    tp = StaticTokenProvider(token)
    legacy_client = DatasetsClient(
        DatasetServices(PalantirContext(hostname=hp, auth=tp))
    )

    print(f"Processing {len(DATASETS)} datasets...\n")

    for name in DATASETS:
        print(f"=== {name} ===")

        # Get RID
        try:
            res = fd_client.filesystem.Resource.get_by_path(
                path=f"{PROJECT}/{name}", preview=True
            )
            rid = res.rid
        except Exception as e:
            print(f"  ❌ RID lookup failed: {e}")
            continue

        # Read via foundry-sdk (newer, handles dataset state better)
        try:
            response = fd_client.datasets.Dataset.read_table(rid, format="ARROW")
            df = response.to_pandas()
            print(f"  Read: {len(df):,} × {len(df.columns)}")
        except Exception as e:
            print(f"  ❌ Read failed: {e}")
            continue

        # Check current type
        if TS_COL not in df.columns:
            print(f"  ⚠️  Column '{TS_COL}' missing — skipping")
            continue

        current_dtype = df[TS_COL].dtype
        print(f"  Current '{TS_COL}' dtype: {current_dtype}")

        if pd.api.types.is_datetime64_any_dtype(current_dtype):
            print(f"  ✓ Already datetime — skipping upload")
            continue

        # Cast
        try:
            df[TS_COL] = pd.to_datetime(df[TS_COL], utc=True, errors="coerce")
            n_nat = df[TS_COL].isna().sum()
            print(f"  Cast → datetime64[ns, UTC]  (NaT: {n_nat})")
        except Exception as e:
            print(f"  ❌ Cast failed: {e}")
            continue

        # Fix other dtypes + re-upload via legacy SDK
        df = fix_dtypes_for_foundry(df)

        try:
            ds = Dataset(legacy_client, DatasetLocator(rid, "master"))
            ds.write_pandas(df)
            print(f"  ✓ Re-uploaded with timestamp cast")
        except Exception as e:
            print(f"  ❌ Upload failed: {type(e).__name__}: {str(e)[:200]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
