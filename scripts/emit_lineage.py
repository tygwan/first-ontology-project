"""Emit OpenLineage events for the BIM pipeline.

Usage:
    .venv/bin/python scripts/emit_lineage.py

Output:
    data/lineage/{SNAPSHOT}/openlineage-events.jsonl
    data/lineage/{SNAPSHOT}/openlineage-summary.json
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bimkg.lineage import emit_pipeline_events


def main() -> int:
    events_path, summary_path = emit_pipeline_events()
    print(f"OpenLineage events:  {events_path}  ({events_path.stat().st_size:,} bytes)")
    print(f"Summary:             {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
