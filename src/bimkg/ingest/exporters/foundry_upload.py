"""Foundry dataset upload via palantir-sdk.

Handles the pandas 2.x string dtype compatibility issue:
- pandas 2.2+ defaults `future.infer_string=True`, creating `str` dtype
- palantir-sdk only recognizes numpy `object` dtype as string
- All-null object columns cause IndexError in schema detection

Fix: set `future.infer_string=False` before read + fill all-null string
columns with empty string.

Usage:
    python -m bimkg.ingest.exporters.foundry_upload
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# CRITICAL: must be set BEFORE any parquet read
pd.set_option("future.infer_string", False)

from palantir.core.config import StaticHostnameProvider, StaticTokenProvider
from palantir.datasets.client import (
    PalantirContext,
    DatasetServices,
    DatasetsClient,
    DatasetLocator,
)
from palantir.datasets.core import Dataset

from bimkg import config

# ---------------------------------------------------------------------------
# Foundry connection
# ---------------------------------------------------------------------------

#: Dataset RIDs in the BIM-KG project (created 2026-04-13)
DATASET_RIDS: dict[str, str] = {
    # Object Types
    "piping": "ri.foundry.main.dataset.778244d2-0ce5-44a2-a435-71779b88ce2d",
    "structural": "ri.foundry.main.dataset.8eeea063-8f0d-4f23-bcf5-d4173288d781",
    "equipment": "ri.foundry.main.dataset.11fdd704-8222-4d6d-83c5-da6ef1fc6f81",
    "electrical": "ri.foundry.main.dataset.84025009-9f7a-42a6-a1f9-109d9417feb1",
    "hvac": "ri.foundry.main.dataset.550025af-28ad-4295-a34f-d20e4f7aa8cf",
    "other": "ri.foundry.main.dataset.93fce9fa-a4c1-4f2a-b190-2e4d4d9c573c",
    # Link Types
    "adjacent_to": "ri.foundry.main.dataset.7cfeea67-54bb-4b61-a4f9-d1f93a4bb00b",
    "has_parent": "ri.foundry.main.dataset.7bda3303-25b2-4920-ba80-fbfcc16b43dc",
    "belongs_to_pipeline": "ri.foundry.main.dataset.4584de0b-0a91-4877-a042-a66c25a7dc7c",
    "in_group": "ri.foundry.main.dataset.f06741ac-d37f-49ca-9473-018fc73a8ea6",
}

LOCAL_FILES: dict[str, Path] = {
    "piping": config.ONTOLOGY_OBJECT_TYPES / "piping.parquet",
    "structural": config.ONTOLOGY_OBJECT_TYPES / "structural.parquet",
    "equipment": config.ONTOLOGY_OBJECT_TYPES / "equipment.parquet",
    "electrical": config.ONTOLOGY_OBJECT_TYPES / "electrical.parquet",
    "hvac": config.ONTOLOGY_OBJECT_TYPES / "hvac.parquet",
    "other": config.ONTOLOGY_OBJECT_TYPES / "other.parquet",
    "adjacent_to": config.ONTOLOGY_LINK_TYPES / "adjacent_to.parquet",
    "has_parent": config.ONTOLOGY_LINK_TYPES / "has_parent.parquet",
    "belongs_to_pipeline": config.ONTOLOGY_LINK_TYPES / "belongs_to_pipeline.parquet",
    "in_group": config.ONTOLOGY_LINK_TYPES / "in_group.parquet",
}


def fix_dtypes_for_foundry(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame dtypes to palantir-sdk compatible types.

    Fixes two issues in pandas 2.x + palantir-sdk 0.12:

    1. **str dtype**: pandas 2.2+ infers `str` (pyarrow-backed) for string
       columns. palantir-sdk only recognizes numpy `object`. Fixed by setting
       `future.infer_string=False` globally (see module top).

    2. **All-null object columns**: palantir-sdk's `_get_field()` does
       `obj[obj.index[0]]` which fails with IndexError on all-null Series.
       Fixed by filling with empty string.

    3. **Nullable Int64**: pandas extension type not recognized by SDK.
       Converted to float64.
    """
    for col in df.columns:
        dt = str(df[col].dtype)
        if dt == "Int64":
            df[col] = df[col].astype("float64")
        elif df[col].dtype == object:
            if df[col].isna().all():
                df[col] = ""
            else:
                df[col] = df[col].fillna("")
    return df


def create_foundry_client(
    hostname: str = "datayoon.usw-18.palantirfoundry.com",
    token: str | None = None,
) -> DatasetsClient:
    """Create a Foundry DatasetsClient.

    Token can be passed directly or read from FOUNDRY_TOKEN env var.
    """
    import os

    if token is None:
        token = os.environ.get("FOUNDRY_TOKEN", "")
    if not token:
        raise ValueError("No token. Set FOUNDRY_TOKEN env var or pass token=")

    hp = StaticHostnameProvider(hostname)
    tp = StaticTokenProvider(token)
    ctx = PalantirContext(hostname=hp, auth=tp)
    return DatasetsClient(DatasetServices(ctx))


def upload_all(
    client: DatasetsClient | None = None,
    token: str | None = None,
) -> dict[str, str]:
    """Upload all 10 datasets to Foundry. Returns {name: status}."""
    if client is None:
        client = create_foundry_client(token=token)

    results = {}
    for name, rid in DATASET_RIDS.items():
        local = LOCAL_FILES[name]
        if not local.exists():
            results[name] = f"SKIP: {local} not found"
            continue

        df = fix_dtypes_for_foundry(pd.read_parquet(local))
        locator = DatasetLocator(rid, "main")
        ds = Dataset(client, locator)

        try:
            ds.write_pandas(df)
            results[name] = f"OK: {len(df):,} rows × {len(df.columns)} cols"
        except Exception as e:
            results[name] = f"ERROR: {str(e)[:150]}"

    return results


if __name__ == "__main__":
    results = upload_all()
    for name, status in results.items():
        print(f"  {name:25s}: {status}")
