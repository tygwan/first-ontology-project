"""ABox instance generator — Gold parquet → RDF triples.

Produces three Turtle files per Q6-C (concern-based split):

- ``bim-shared.ttl``  — Pipeline, PipeRun, Level, Material, Spec individuals
- ``bim-objects.ttl``  — 12,009 BIMEntity individuals with data properties
- ``bim-spatial.ttl``  — 220K adjacency triples (symmetric)

Design decisions applied:
- Q2-C: Equipment subclasses from Eqp Type 0 + UnclassifiedEquipment
- Q3-C: classificationConfidence as data property on all objects
- Q5-B: Pipeline/PipeRun as named individuals (URI)
- Q7-A: xsd:double with unit suffix in property name
- Q8-B: spatial triples generated from adjacency.parquet (not DXTnavis TTL)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from bimkg import config
from bimkg.ontology.namespaces import BIM, INST, NAMESPACE_BINDINGS, SPATIAL
from bimkg.ontology.schema import EQP_TYPE_0_MAP, REFINED_CLASS_MAP


def _bind_namespaces(g: Graph) -> None:
    for prefix, ns in NAMESPACE_BINDINGS.items():
        g.bind(prefix, ns)


def _safe_uri(raw: str) -> str:
    """Convert a raw string to a URI-safe local name."""
    s = re.sub(r"[^A-Za-z0-9_-]", "_", raw.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


# ---------------------------------------------------------------------------
# Shared individuals (Pipeline, PipeRun, Level, Material, Spec)
# ---------------------------------------------------------------------------


def build_shared(gold: pd.DataFrame) -> Graph:
    """Create named individuals for shared-reference entities."""
    g = Graph()
    _bind_namespaces(g)

    _add_pipelines(g, gold)
    _add_pipe_runs(g, gold)
    _add_levels(g, gold)
    _add_materials(g, gold)
    _add_specifications(g, gold)

    return g


def _add_pipelines(g: Graph, gold: pd.DataFrame) -> None:
    names = gold["sp3d_pipeline"].dropna().unique()
    for name in sorted(names):
        uri = INST[f"pipeline-{_safe_uri(name)}"]
        g.add((uri, RDF.type, BIM.Pipeline))
        g.add((uri, BIM.pipelineName, Literal(name, datatype=XSD.string)))


def _add_pipe_runs(g: Graph, gold: pd.DataFrame) -> None:
    names = gold["sp3d_pipe_run"].dropna().unique()
    for name in sorted(names):
        uri = INST[f"piperun-{_safe_uri(name)}"]
        g.add((uri, RDF.type, BIM.PipeRun))
        g.add((uri, BIM.pipeRunName, Literal(name, datatype=XSD.string)))


def _add_levels(g: Graph, gold: pd.DataFrame) -> None:
    levels = gold["level"].dropna().unique()
    for lv in sorted(int(x) for x in levels):
        uri = INST[f"level-{lv}"]
        g.add((uri, RDF.type, BIM.Level))
        g.add((uri, BIM.levelValue, Literal(lv, datatype=XSD.integer)))


def _add_materials(g: Graph, gold: pd.DataFrame) -> None:
    if "sp3d_material" not in gold.columns:
        return
    names = gold["sp3d_material"].dropna().unique()
    for name in sorted(names):
        uri = INST[f"material-{_safe_uri(name)}"]
        g.add((uri, RDF.type, BIM.Material))
        g.add((uri, BIM.materialName, Literal(name, datatype=XSD.string)))


def _add_specifications(g: Graph, gold: pd.DataFrame) -> None:
    if "sp3d_spec_name" not in gold.columns:
        return
    names = gold["sp3d_spec_name"].dropna().unique()
    for name in sorted(names):
        uri = INST[f"spec-{_safe_uri(name)}"]
        g.add((uri, RDF.type, BIM.Specification))
        g.add((uri, BIM.specificationName, Literal(name, datatype=XSD.string)))


# ---------------------------------------------------------------------------
# Object individuals (12,009 BIMEntity instances)
# ---------------------------------------------------------------------------


def build_objects(gold: pd.DataFrame) -> Graph:
    """Create individuals for every BIM object with typed class + data props."""
    g = Graph()
    _bind_namespaces(g)

    for _, row in gold.iterrows():
        oid = row["object_id"]
        uri = INST[oid]

        _assign_type(g, uri, row)
        _add_identity_props(g, uri, row)
        _add_geometry_props(g, uri, row)
        _add_physical_props(g, uri, row)
        _add_piping_props(g, uri, row)
        _add_flag_props(g, uri, row)
        _add_confidence_props(g, uri, row)
        _add_object_links(g, uri, row)

    return g


def _assign_type(g: Graph, uri: URIRef, row: pd.Series) -> None:
    """Assign rdf:type based on flags and refined_class."""
    if row.get("is_analysis_volume"):
        g.add((uri, RDF.type, BIM.AnalysisVolume))
        return
    if row.get("is_container"):
        g.add((uri, RDF.type, BIM.HierarchyNode))
        return
    if row.get("is_parent_box"):
        g.add((uri, RDF.type, BIM.HierarchyNode))  # parent box = hierarchy node
        return

    refined = row.get("refined_class", "Other")
    owl_class = REFINED_CLASS_MAP.get(refined, "UncategorizedObject")

    if owl_class == "Equipment":
        eqp_type = row.get("sp3d_eqp_type_0")
        if pd.notna(eqp_type) and eqp_type in EQP_TYPE_0_MAP:
            owl_class = EQP_TYPE_0_MAP[eqp_type]
        else:
            owl_class = "UnclassifiedEquipment"

    g.add((uri, RDF.type, BIM[owl_class]))


def _add_str(
    g: Graph, uri: URIRef, prop: URIRef, row: pd.Series, col: str
) -> None:
    val = row.get(col)
    if pd.notna(val) and str(val).strip():
        g.add((uri, prop, Literal(str(val), datatype=XSD.string)))


def _add_double(
    g: Graph, uri: URIRef, prop: URIRef, row: pd.Series, col: str
) -> None:
    val = row.get(col)
    if pd.notna(val):
        g.add((uri, prop, Literal(float(val), datatype=XSD.double)))


def _add_int(
    g: Graph, uri: URIRef, prop: URIRef, row: pd.Series, col: str
) -> None:
    val = row.get(col)
    if pd.notna(val):
        g.add((uri, prop, Literal(int(val), datatype=XSD.integer)))


def _add_bool(
    g: Graph, uri: URIRef, prop: URIRef, row: pd.Series, col: str
) -> None:
    val = row.get(col)
    if pd.notna(val):
        g.add((uri, prop, Literal(bool(val), datatype=XSD.boolean)))


def _add_identity_props(g: Graph, uri: URIRef, row: pd.Series) -> None:
    _add_str(g, uri, BIM.objectId, row, "object_id")
    _add_str(g, uri, BIM.displayName, row, "display_name")
    _add_str(g, uri, BIM.systemPath, row, "system_path")
    _add_int(g, uri, BIM.level, row, "level")
    _add_str(g, uri, BIM.refinedClass, row, "refined_class")


def _add_geometry_props(g: Graph, uri: URIRef, row: pd.Series) -> None:
    _add_double(g, uri, BIM.centroidX, row, "centroid_x")
    _add_double(g, uri, BIM.centroidY, row, "centroid_y")
    _add_double(g, uri, BIM.centroidZ, row, "centroid_z")
    _add_double(g, uri, BIM.bboxVolumeM3, row, "bbox_volume_m3")
    _add_int(g, uri, BIM.vertexCount, row, "vertex_count")
    _add_int(g, uri, BIM.triangleCount, row, "triangle_count")
    _add_bool(g, uri, BIM.hasRealMesh, row, "has_real_mesh")


def _add_physical_props(g: Graph, uri: URIRef, row: pd.Series) -> None:
    _add_double(g, uri, BIM.dryWeightKg, row, "dry_weight_kg")
    _add_double(g, uri, BIM.wetWeightKg, row, "wet_weight_kg")
    _add_double(g, uri, BIM.lengthM, row, "length_m")
    _add_double(g, uri, BIM.designPressureKpa, row, "design_pressure_kpa")
    _add_double(g, uri, BIM.designTemperatureC, row, "design_temperature_c")


def _add_piping_props(g: Graph, uri: URIRef, row: pd.Series) -> None:
    _add_str(g, uri, BIM.commodityCode, row, "sp3d_commodity_code")
    _add_str(g, uri, BIM.npd, row, "sp3d_npd")
    _add_str(g, uri, BIM.specName, row, "sp3d_spec_name")


def _add_flag_props(g: Graph, uri: URIRef, row: pd.Series) -> None:
    _add_bool(g, uri, BIM.isContainer, row, "is_container")
    _add_bool(g, uri, BIM.isAnalysisVolume, row, "is_analysis_volume")


def _add_confidence_props(g: Graph, uri: URIRef, row: pd.Series) -> None:
    _add_str(g, uri, BIM.classificationConfidence, row, "classification_confidence")
    _add_str(g, uri, BIM.classificationConfidenceReason, row, "classification_confidence_reason")


def _add_object_links(g: Graph, uri: URIRef, row: pd.Series) -> None:
    # belongsToPipeline (Q5-B)
    pipeline = row.get("sp3d_pipeline")
    if pd.notna(pipeline) and str(pipeline).strip():
        g.add((uri, BIM.belongsToPipeline, INST[f"pipeline-{_safe_uri(str(pipeline))}"]))

    # belongsToPipeRun
    piperun = row.get("sp3d_pipe_run")
    if pd.notna(piperun) and str(piperun).strip():
        g.add((uri, BIM.belongsToPipeRun, INST[f"piperun-{_safe_uri(str(piperun))}"]))

    # hasParent
    parent = row.get("parent_id")
    if pd.notna(parent) and str(parent).strip():
        g.add((uri, BIM.hasParent, INST[str(parent)]))

    # atLevel
    lv = row.get("level")
    if pd.notna(lv):
        g.add((uri, BIM.atLevel, INST[f"level-{int(lv)}"]))

    # hasMaterial
    mat = row.get("sp3d_material")
    if pd.notna(mat) and str(mat).strip():
        g.add((uri, BIM.hasMaterial, INST[f"material-{_safe_uri(str(mat))}"]))

    # hasSpecification
    spec = row.get("sp3d_spec_name")
    if pd.notna(spec) and str(spec).strip():
        g.add((uri, BIM.hasSpecification, INST[f"spec-{_safe_uri(str(spec))}"]))

    # inGroup
    gid = row.get("group_id")
    if pd.notna(gid) and str(gid).strip():
        g.add((uri, BIM.inGroup, INST[f"group-{_safe_uri(str(gid))}"]))


# ---------------------------------------------------------------------------
# Spatial triples (adjacency)
# ---------------------------------------------------------------------------


def build_spatial(adjacency: pd.DataFrame) -> Graph:
    """Create adjacency triples from the symmetric adjacency table."""
    g = Graph()
    _bind_namespaces(g)

    for _, row in adjacency.iterrows():
        src = INST[str(row["source_object_id"])]
        tgt = INST[str(row["target_object_id"])]
        g.add((src, BIM.adjacentTo, tgt))

    return g


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------


def generate_abox(
    gold: pd.DataFrame | None = None,
    adjacency: pd.DataFrame | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Generate all three ABox files. Returns {name: path} dict."""
    if gold is None:
        gold = pd.read_parquet(config.ENRICHED_OBJECTS)
    if adjacency is None:
        adjacency = pd.read_parquet(config.ENRICHED_ADJACENCY_SYM)
    if output_dir is None:
        output_dir = config.ONTOLOGY_OWL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    shared_path = output_dir / "bim-shared.ttl"
    g_shared = build_shared(gold)
    g_shared.serialize(destination=str(shared_path), format="turtle")
    paths["shared"] = shared_path

    objects_path = output_dir / "bim-objects.ttl"
    g_objects = build_objects(gold)
    g_objects.serialize(destination=str(objects_path), format="turtle")
    paths["objects"] = objects_path

    spatial_path = output_dir / "bim-spatial.ttl"
    g_spatial = build_spatial(adjacency)
    g_spatial.serialize(destination=str(spatial_path), format="turtle")
    paths["spatial"] = spatial_path

    return paths
