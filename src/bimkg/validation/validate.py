"""SHACL validation runner.

Loads TBox + ABox + SHACL shapes, runs pySHACL, and produces
a structured validation report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pyshacl
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from bimkg import config
from bimkg.ontology.namespaces import BIM, NAMESPACE_BINDINGS

SH = URIRef("http://www.w3.org/ns/shacl#")


@dataclass
class ValidationResult:
    """Structured result from a SHACL validation run."""

    conforms: bool
    total_violations: int
    by_severity: dict[str, int] = field(default_factory=dict)
    by_shape: dict[str, int] = field(default_factory=dict)
    violations: list[dict] = field(default_factory=list)


def run_validation(
    data_graph: Graph | None = None,
    shapes_graph: Graph | None = None,
    max_violations: int = 1000,
) -> ValidationResult:
    """Run SHACL validation and return structured results.

    Parameters
    ----------
    data_graph : Graph, optional
        Combined TBox + ABox graph. If None, loads from default paths.
    shapes_graph : Graph, optional
        SHACL shapes graph. If None, loads from default path.
    max_violations : int
        Maximum number of individual violations to collect (for memory).
    """
    if data_graph is None:
        data_graph = _load_data_graph()
    if shapes_graph is None:
        shapes_graph = _load_shapes_graph()

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference="none",
        abort_on_first=False,
    )

    return _parse_results(conforms, results_graph, max_violations)


def _load_data_graph() -> Graph:
    g = Graph()
    for prefix, ns in NAMESPACE_BINDINGS.items():
        g.bind(prefix, ns)
    g.parse(str(config.ONTOLOGY_OWL), format="turtle")
    g.parse(str(config.ONTOLOGY_OWL_DIR / "bim-shared.ttl"), format="turtle")
    g.parse(str(config.ONTOLOGY_OWL_DIR / "bim-objects.ttl"), format="turtle")
    return g


def _load_shapes_graph() -> Graph:
    g = Graph()
    g.parse(str(config.ONTOLOGY_SHAPES), format="turtle")
    return g


def _parse_results(
    conforms: bool,
    results_graph: Graph,
    max_violations: int,
) -> ValidationResult:
    """Parse the pySHACL results graph into a structured report."""
    SH_NS = "http://www.w3.org/ns/shacl#"
    result_class = URIRef(f"{SH_NS}ValidationResult")
    source_shape_pred = URIRef(f"{SH_NS}sourceShape")
    focus_node_pred = URIRef(f"{SH_NS}focusNode")
    message_pred = URIRef(f"{SH_NS}resultMessage")
    severity_pred = URIRef(f"{SH_NS}resultSeverity")

    violations = []
    by_severity: dict[str, int] = {}
    by_shape: dict[str, int] = {}

    for result_node in results_graph.subjects(RDF.type, result_class):
        sev = str(list(results_graph.objects(result_node, severity_pred))[0]).split("#")[-1]
        shape = str(list(results_graph.objects(result_node, source_shape_pred))[0]).split("/")[-1]
        focus = str(list(results_graph.objects(result_node, focus_node_pred))[0]).split("/")[-1]
        msgs = list(results_graph.objects(result_node, message_pred))
        msg = str(msgs[0]) if msgs else ""

        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_shape[shape] = by_shape.get(shape, 0) + 1

        if len(violations) < max_violations:
            violations.append({
                "severity": sev,
                "shape": shape,
                "focus_node": focus,
                "message": msg,
            })

    return ValidationResult(
        conforms=conforms,
        total_violations=sum(by_severity.values()),
        by_severity=by_severity,
        by_shape=by_shape,
        violations=violations,
    )


def print_report(result: ValidationResult) -> None:
    """Print a human-readable validation report."""
    status = "PASS" if result.conforms else "FAIL"
    print(f"=== SHACL Validation: {status} ({result.total_violations} violations) ===\n")

    if result.by_severity:
        print("By severity:")
        for sev, cnt in sorted(result.by_severity.items()):
            print(f"  {sev:15s}: {cnt:>6,}")

    if result.by_shape:
        print("\nBy shape:")
        for shape, cnt in sorted(result.by_shape.items(), key=lambda x: -x[1]):
            print(f"  {shape:45s}: {cnt:>6,}")

    if result.violations:
        print(f"\nSample violations (first {min(10, len(result.violations))}):")
        for v in result.violations[:10]:
            print(f"  [{v['severity']:9s}] {v['shape']:40s} → {v['focus_node'][:40]}")
            if v["message"]:
                print(f"             {v['message'][:80]}")
