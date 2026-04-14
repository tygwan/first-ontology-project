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

#: Dataset RIDs in the BIM-KG project (updated 2026-04-15 — bim_* prefix).
#: These are resolved from Compass paths ``/Datayoon-09825c/BIM-KG/<name>``
#: via ``client.get_dataset(path)`` at upload time if this dict goes stale.
DATASET_RIDS: dict[str, str] = {
    # Object Types (6) — class-split BIM objects (12,009 total)
    "piping": "ri.foundry.main.dataset.2388ddc2-3c83-4ef3-a7df-fef11024bb4e",
    "structural": "ri.foundry.main.dataset.32658e86-ad1b-4adb-8acf-c3c409a21661",
    "equipment": "ri.foundry.main.dataset.5e250030-37c1-4475-aaac-8a9e9bf42e64",
    "electrical": "ri.foundry.main.dataset.29338c90-e5be-4db7-86f9-eb0449340873",
    "hvac": "ri.foundry.main.dataset.914af224-32c8-48c5-b419-47eab341e33b",
    "other": "ri.foundry.main.dataset.87c921ea-cfcb-4ba5-b656-4bcacde11804",
    # Link Types (4) — 137,116 relationship rows
    "adjacent_to": "ri.foundry.main.dataset.d6f789d4-54d7-49d1-9351-b20e825624dc",
    "has_parent": "ri.foundry.main.dataset.159d949e-fe9b-4267-a20e-57512e0600d8",
    "belongs_to_pipeline": "ri.foundry.main.dataset.97db7363-a24e-4cd8-870c-39450ba9bbfa",
    "in_group": "ri.foundry.main.dataset.0e57446a-bbc6-4443-bec8-7cbf58103e65",
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


OBJECT_TYPES: tuple[str, ...] = (
    "piping", "structural", "equipment", "electrical", "hvac", "other",
)
LINK_TYPES: tuple[str, ...] = (
    "adjacent_to", "has_parent", "belongs_to_pipeline", "in_group",
)


def upload_all(
    client: DatasetsClient | None = None,
    token: str | None = None,
    only: tuple[str, ...] | None = None,
) -> dict[str, str]:
    """Upload datasets to Foundry.

    Parameters
    ----------
    only : optional tuple of dataset names
        If provided, upload only those datasets (subset of DATASET_RIDS keys).
        Example: ``only=LINK_TYPES`` uploads just the 4 link datasets.
    """
    if client is None:
        client = create_foundry_client(token=token)

    targets = DATASET_RIDS if only is None else {k: DATASET_RIDS[k] for k in only}

    results = {}
    for name, rid in targets.items():
        local = LOCAL_FILES[name]
        if not local.exists():
            results[name] = f"SKIP: {local} not found"
            continue

        df = fix_dtypes_for_foundry(pd.read_parquet(local))
        locator = DatasetLocator(rid, "master")
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
