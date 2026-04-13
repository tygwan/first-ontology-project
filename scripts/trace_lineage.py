"""Build upstream/downstream lineage report from emitted OpenLineage events.

Reads:    data/lineage/{SNAPSHOT}/openlineage-events.jsonl
Writes:   docs/reference/lineage/{SNAPSHOT}/lineage-graph.json
          docs/reference/lineage/{SNAPSHOT}/impact-analysis.md
          docs/reference/lineage/{SNAPSHOT}/lineage-graph.dot

Use cases:
    "If we change AllProperties.csv, what downstream artifacts break?"
    "Which Bronze sources feed the Foundry Equipment dataset?"
    "What is the dependency depth of the SHACL shapes?"

Usage:
    .venv/bin/python scripts/trace_lineage.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bimkg import config


def load_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def _key(ds: dict) -> str:
    return f"{ds['namespace']}::{ds['name']}"


def build_graph(events: list[dict]) -> dict:
    """Produce a bipartite graph of jobs and datasets with edges."""
    jobs: dict[str, dict] = {}
    datasets: dict[str, dict] = {}
    edges_in: list[tuple[str, str]] = []   # dataset -> job
    edges_out: list[tuple[str, str]] = []  # job -> dataset

    for ev in events:
        if ev["eventType"] != "COMPLETE":
            continue
        job_name = ev["job"]["name"]
        if job_name not in jobs:
            jobs[job_name] = {
                "name": job_name,
                "namespace": ev["job"]["namespace"],
                "description": ev["job"]
                .get("facets", {})
                .get("documentation", {})
                .get("description", ""),
                "source_path": ev["job"]
                .get("facets", {})
                .get("sourceCodeLocation", {})
                .get("path", ""),
            }
        for ds in ev.get("inputs", []) or []:
            k = _key(ds)
            if k not in datasets:
                datasets[k] = {
                    "key": k,
                    "namespace": ds["namespace"],
                    "name": ds["name"],
                    "description": ds.get("facets", {})
                    .get("documentation", {})
                    .get("description", ""),
                }
            edges_in.append((k, job_name))
        for ds in ev.get("outputs", []) or []:
            k = _key(ds)
            if k not in datasets:
                datasets[k] = {
                    "key": k,
                    "namespace": ds["namespace"],
                    "name": ds["name"],
                    "description": ds.get("facets", {})
                    .get("documentation", {})
                    .get("description", ""),
                }
            edges_out.append((job_name, k))

    return {
        "jobs": jobs,
        "datasets": datasets,
        "edges_in": edges_in,
        "edges_out": edges_out,
    }


def build_adjacency(graph: dict) -> tuple[dict, dict]:
    """Returns (downstream, upstream) maps keyed by dataset key.

    downstream[ds] = list of datasets reachable downstream
    upstream[ds]   = list of datasets that contribute upstream
    """
    # ds -> jobs that consume it
    consumers: dict[str, list[str]] = defaultdict(list)
    for ds, job in graph["edges_in"]:
        consumers[ds].append(job)
    # job -> datasets it produces
    job_outputs: dict[str, list[str]] = defaultdict(list)
    for job, ds in graph["edges_out"]:
        job_outputs[job].append(ds)
    # job -> datasets it consumes
    job_inputs: dict[str, list[str]] = defaultdict(list)
    for ds, job in graph["edges_in"]:
        job_inputs[job].append(ds)
    # ds -> jobs that produce it
    producers: dict[str, list[str]] = defaultdict(list)
    for job, ds in graph["edges_out"]:
        producers[ds].append(job)

    def downstream(ds: str, visited: set | None = None) -> list[str]:
        visited = visited or set()
        result: list[str] = []
        for job in consumers.get(ds, []):
            for out_ds in job_outputs.get(job, []):
                if out_ds in visited:
                    continue
                visited.add(out_ds)
                result.append(out_ds)
                result.extend(downstream(out_ds, visited))
        return result

    def upstream(ds: str, visited: set | None = None) -> list[str]:
        visited = visited or set()
        result: list[str] = []
        for job in producers.get(ds, []):
            for in_ds in job_inputs.get(job, []):
                if in_ds in visited:
                    continue
                visited.add(in_ds)
                result.append(in_ds)
                result.extend(upstream(in_ds, visited))
        return result

    down_map = {k: downstream(k) for k in graph["datasets"]}
    up_map = {k: upstream(k) for k in graph["datasets"]}
    return down_map, up_map


def write_dot(graph: dict, out_path: Path) -> None:
    lines = ["digraph lineage {", "  rankdir=LR;", "  node [shape=box, style=filled];"]
    for k, ds in graph["datasets"].items():
        ns = ds["namespace"]
        if ns.startswith("file://"):
            color = "lightyellow" if "/raw/" in ds["name"] else "palegreen"
            label = ds["name"].split("/")[-1] or "dir/"
        elif ns.startswith("sqlite://"):
            color = "lightblue"
            label = "sqlite:" + ds["name"]
        elif ns.startswith("palantir-foundry"):
            color = "lavender"
            label = ds["name"].split("/")[-1]
        else:
            color = "white"
            label = ds["name"][-40:]
        lines.append(f'  "{k}" [label="{label}", fillcolor={color}];')
    for j, job in graph["jobs"].items():
        lines.append(f'  "job::{j}" [label="{j}", shape=ellipse, fillcolor=lightcoral];')
    for ds, job in graph["edges_in"]:
        lines.append(f'  "{ds}" -> "job::{job}";')
    for job, ds in graph["edges_out"]:
        lines.append(f'  "job::{job}" -> "{ds}";')
    lines.append("}")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown(
    graph: dict,
    down_map: dict[str, list[str]],
    up_map: dict[str, list[str]],
    out_path: Path,
) -> None:
    lines = []
    lines.append(f"# Lineage Impact Analysis — {config.SNAPSHOT}\n")
    lines.append(
        "> Generated by `scripts/trace_lineage.py` from the emitted OpenLineage events.\n"
        "> Use this when you need to know what breaks if you change a dataset.\n"
    )

    lines.append("## Datasets at a glance\n")
    lines.append("| # | Namespace | Name | Type |")
    lines.append("|---|-----------|------|------|")
    for i, (k, ds) in enumerate(sorted(graph["datasets"].items()), start=1):
        ns = ds["namespace"]
        kind = (
            "Bronze" if "/raw/" in ds["name"]
            else "Gold" if "/enriched/" in ds["name"]
            else "Output"
        )
        if ns.startswith("sqlite://"):
            kind = "Warehouse"
        if ns.startswith("palantir-foundry"):
            kind = "Foundry"
        lines.append(f"| {i} | `{ns[:40]}` | `{ds['name']}` | {kind} |")

    lines.append("\n## Jobs\n")
    lines.append("| Job | Source file | Inputs | Outputs |")
    lines.append("|-----|-------------|-------:|--------:|")
    in_count: dict[str, int] = defaultdict(int)
    out_count: dict[str, int] = defaultdict(int)
    for ds, job in graph["edges_in"]:
        in_count[job] += 1
    for job, ds in graph["edges_out"]:
        out_count[job] += 1
    for jname, j in sorted(graph["jobs"].items()):
        lines.append(
            f"| `{jname}` | `{j['source_path']}` | {in_count[jname]} | {out_count[jname]} |"
        )

    lines.append("\n## Downstream impact\n")
    lines.append("> If you change the LEFT dataset, the RIGHT artifacts must be regenerated.\n")
    for k in sorted(graph["datasets"]):
        downs = down_map.get(k, [])
        if not downs:
            continue
        ds = graph["datasets"][k]
        lines.append(f"### `{ds['name']}`\n")
        for d in downs:
            tgt = graph["datasets"][d]
            lines.append(f"- `{tgt['name']}`")
        lines.append("")

    lines.append("\n## Upstream provenance\n")
    lines.append("> The LEFT dataset is built from the RIGHT sources.\n")
    for k in sorted(graph["datasets"]):
        ups = up_map.get(k, [])
        if not ups:
            continue
        ds = graph["datasets"][k]
        lines.append(f"### `{ds['name']}`\n")
        for u in ups:
            src = graph["datasets"][u]
            lines.append(f"- `{src['name']}`")
        lines.append("")

    lines.append("\n## Sample queries\n")
    lines.append(
        "```text\n"
        "Q: If we change AllProperties_20260407_184650.csv, what breaks?\n"
        "A: See section 'Downstream impact' for "
        "data/raw/dxtnavis/2026-04-12/AllProperties_20260407_184650.csv.\n"
        "\n"
        "Q: What feeds bim_objects_enriched.parquet?\n"
        "A: See 'Upstream provenance' for data/enriched/2026-04-12/bim_objects_enriched.parquet.\n"
        "```\n"
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    events_path = config.DATA_ROOT / "lineage" / config.SNAPSHOT / "openlineage-events.jsonl"
    if not events_path.exists():
        print(f"[!] Lineage events not found at {events_path}")
        print("    Run: .venv/bin/python scripts/emit_lineage.py")
        return 1

    out_dir = PROJECT_ROOT / "docs" / "reference" / "lineage" / config.SNAPSHOT
    out_dir.mkdir(parents=True, exist_ok=True)

    events = load_events(events_path)
    graph = build_graph(events)
    down_map, up_map = build_adjacency(graph)

    json_path = out_dir / "lineage-graph.json"
    md_path = out_dir / "impact-analysis.md"
    dot_path = out_dir / "lineage-graph.dot"

    json_path.write_text(
        json.dumps(
            {
                "snapshot": config.SNAPSHOT,
                "jobs": graph["jobs"],
                "datasets": graph["datasets"],
                "edges_in": graph["edges_in"],
                "edges_out": graph["edges_out"],
                "downstream": down_map,
                "upstream": up_map,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_markdown(graph, down_map, up_map, md_path)
    write_dot(graph, dot_path)

    print(f"[OK] {json_path}  ({json_path.stat().st_size:,} bytes)")
    print(f"[OK] {md_path}    ({md_path.stat().st_size:,} bytes)")
    print(f"[OK] {dot_path}   (render with:  dot -Tpng {dot_path.name} -o lineage.png)")
    print(f"[OK] {len(graph['jobs'])} jobs, {len(graph['datasets'])} datasets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
