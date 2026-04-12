"""OWL TBox generator for the BIM ontology.

Produces the class hierarchy (D10 sibling structure), object properties,
and data properties as an rdflib Graph serialised to OWL/Turtle.

Class hierarchy
===============

::

    BIMEntity
    ├── BIMObject
    │   ├── PhysicalObject
    │   │   ├── PipingComponent
    │   │   ├── StructuralMember
    │   │   ├── Equipment
    │   │   │   ├── ProcessEquipment
    │   │   │   ├── ElectricalEquipment
    │   │   │   ├── ArchitecturalEquipment
    │   │   │   ├── HvacEquipment
    │   │   │   ├── CivilElements
    │   │   │   ├── CivilEquipment
    │   │   │   ├── BlackBoxSystems
    │   │   │   └── UnclassifiedEquipment
    │   │   ├── ElectricalComponent
    │   │   ├── HvacComponent
    │   │   └── UncategorizedObject
    │   └── Container
    │       └── HierarchyNode
    └── AnalysisArtifact
        └── AnalysisVolume

Decisions: D10 (sibling), Q2-C (equipment subclasses), Q3-C (confidence
annotation), Q5-B (Pipeline/PipeRun as named individuals), Q7-A (xsd:double).
"""

from __future__ import annotations

from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from bimkg import config
from bimkg.ontology.namespaces import BIM, NAMESPACE_BINDINGS

# ---------------------------------------------------------------------------
# Class hierarchy constants
# ---------------------------------------------------------------------------

#: (child, parent) pairs defining rdfs:subClassOf relationships.
CLASS_HIERARCHY: list[tuple[str, str | None]] = [
    # Roots
    ("BIMEntity", None),
    # BIMObject branch
    ("BIMObject", "BIMEntity"),
    ("PhysicalObject", "BIMObject"),
    ("PipingComponent", "PhysicalObject"),
    ("StructuralMember", "PhysicalObject"),
    ("Equipment", "PhysicalObject"),
    ("ElectricalComponent", "PhysicalObject"),
    ("HvacComponent", "PhysicalObject"),
    ("UncategorizedObject", "PhysicalObject"),
    # Equipment subclasses (Q2-C: from Eqp Type 0 values)
    ("ProcessEquipment", "Equipment"),
    ("ElectricalEquipment", "Equipment"),
    ("ArchitecturalEquipment", "Equipment"),
    ("HvacEquipment", "Equipment"),
    ("CivilElements", "Equipment"),
    ("CivilEquipment", "Equipment"),
    ("BlackBoxSystems", "Equipment"),
    ("UnclassifiedEquipment", "Equipment"),
    # Container branch
    ("Container", "BIMObject"),
    ("HierarchyNode", "Container"),
    # AnalysisArtifact branch (D10: sibling of BIMObject)
    ("AnalysisArtifact", "BIMEntity"),
    ("AnalysisVolume", "AnalysisArtifact"),
]

#: Map from Eqp Type 0 raw string → OWL class local name.
EQP_TYPE_0_MAP: dict[str, str] = {
    "Process Equipment": "ProcessEquipment",
    "Electrical Equipment": "ElectricalEquipment",
    "Architectural": "ArchitecturalEquipment",
    "HVAC Equipment": "HvacEquipment",
    "Civil Elements": "CivilElements",
    "Civil Equipment": "CivilEquipment",
    "Black Box Systems": "BlackBoxSystems",
}

#: Map from ``refined_class`` value → OWL class local name.
#: Used by Phase 2b to assign rdf:type to instances.
REFINED_CLASS_MAP: dict[str, str] = {
    "Piping": "PipingComponent",
    "Structure": "StructuralMember",
    "Equipment": "Equipment",
    "Electrical": "ElectricalComponent",
    "HVAC": "HvacComponent",
    "Other": "UncategorizedObject",
}

# ---------------------------------------------------------------------------
# Context classes (shared-reference individuals)
# ---------------------------------------------------------------------------

CONTEXT_CLASSES: list[tuple[str, str | None]] = [
    ("Context", None),
    ("Pipeline", "Context"),
    ("PipeRun", "Context"),
    ("Level", "Context"),
    ("ConnectedGroup", "Context"),
    ("Material", "Context"),
    ("Specification", "Context"),
]

# ---------------------------------------------------------------------------
# Object properties (domain → range)
# ---------------------------------------------------------------------------

#: (local_name, domain, range, flags)
#: flags: "S" = symmetric, "I" = inverse-functional, "F" = functional
OBJECT_PROPERTIES: list[tuple[str, str, str, str]] = [
    ("adjacentTo", "PhysicalObject", "PhysicalObject", "S"),
    ("hasParent", "BIMEntity", "BIMEntity", ""),
    ("belongsToPipeline", "PipingComponent", "Pipeline", ""),
    ("belongsToPipeRun", "PipingComponent", "PipeRun", ""),
    ("hasMaterial", "PhysicalObject", "Material", ""),
    ("hasSpecification", "PhysicalObject", "Specification", ""),
    ("atLevel", "BIMEntity", "Level", ""),
    ("inGroup", "BIMEntity", "ConnectedGroup", ""),
]

# ---------------------------------------------------------------------------
# Data properties (domain, xsd type)
# ---------------------------------------------------------------------------

#: (local_name, domain, xsd_type)
DATA_PROPERTIES: list[tuple[str, str, URIRef]] = [
    # Identity
    ("objectId", "BIMEntity", XSD.string),
    ("displayName", "BIMEntity", XSD.string),
    ("systemPath", "BIMEntity", XSD.string),
    ("level", "BIMEntity", XSD.integer),
    ("refinedClass", "BIMEntity", XSD.string),
    # Confidence (Q3-C)
    ("classificationConfidence", "BIMEntity", XSD.string),
    ("classificationConfidenceReason", "BIMEntity", XSD.string),
    # Geometry
    ("centroidX", "BIMEntity", XSD.double),
    ("centroidY", "BIMEntity", XSD.double),
    ("centroidZ", "BIMEntity", XSD.double),
    ("bboxVolumeM3", "BIMEntity", XSD.double),
    ("vertexCount", "BIMEntity", XSD.integer),
    ("triangleCount", "BIMEntity", XSD.integer),
    ("hasRealMesh", "BIMEntity", XSD.boolean),
    # Physical quantities (Q7-A: xsd:double + unit suffix)
    ("dryWeightKg", "PhysicalObject", XSD.double),
    ("wetWeightKg", "PhysicalObject", XSD.double),
    ("lengthM", "PhysicalObject", XSD.double),
    ("designPressureKpa", "PhysicalObject", XSD.double),
    ("designTemperatureC", "PhysicalObject", XSD.double),
    # Piping-specific
    ("commodityCode", "PipingComponent", XSD.string),
    ("npd", "PipingComponent", XSD.string),
    ("specName", "PipingComponent", XSD.string),
    # Flags
    ("isContainer", "BIMEntity", XSD.boolean),
    ("isAnalysisVolume", "BIMEntity", XSD.boolean),
    ("isGiantGroup", "ConnectedGroup", XSD.boolean),
    # Context properties
    ("pipelineName", "Pipeline", XSD.string),
    ("pipeRunName", "PipeRun", XSD.string),
    ("levelValue", "Level", XSD.integer),
    ("materialName", "Material", XSD.string),
    ("specificationName", "Specification", XSD.string),
    # Adjacency metadata
    ("distanceM", "BIMEntity", XSD.double),
    ("overlapVolumeM3", "BIMEntity", XSD.double),
]


# ---------------------------------------------------------------------------
# TBox builder
# ---------------------------------------------------------------------------


def build_tbox() -> Graph:
    """Build the OWL TBox graph (class hierarchy + properties)."""
    g = Graph()
    for prefix, ns in NAMESPACE_BINDINGS.items():
        g.bind(prefix, ns)

    ontology_uri = BIM["bim-ontology"]
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, RDFS.label, Literal("BIM Plant Ontology")))
    g.add((
        ontology_uri,
        RDFS.comment,
        Literal(
            "OWL ontology for SP3D plant BIM data (12,009 objects). "
            "Generated by bimkg.ontology.schema."
        ),
    ))

    _add_classes(g, CLASS_HIERARCHY)
    _add_classes(g, CONTEXT_CLASSES)
    _add_object_properties(g)
    _add_data_properties(g)

    return g


def _add_classes(
    g: Graph,
    hierarchy: list[tuple[str, str | None]],
) -> None:
    for name, parent in hierarchy:
        cls = BIM[name]
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(name)))
        if parent is not None:
            g.add((cls, RDFS.subClassOf, BIM[parent]))


def _add_object_properties(g: Graph) -> None:
    for name, domain, range_, flags in OBJECT_PROPERTIES:
        prop = BIM[name]
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.label, Literal(name)))
        g.add((prop, RDFS.domain, BIM[domain]))
        g.add((prop, RDFS.range, BIM[range_]))
        if "S" in flags:
            g.add((prop, RDF.type, OWL.SymmetricProperty))
        if "I" in flags:
            g.add((prop, RDF.type, OWL.InverseFunctionalProperty))
        if "F" in flags:
            g.add((prop, RDF.type, OWL.FunctionalProperty))


def _add_data_properties(g: Graph) -> None:
    for name, domain, xsd_type in DATA_PROPERTIES:
        prop = BIM[name]
        g.add((prop, RDF.type, OWL.DatatypeProperty))
        g.add((prop, RDFS.label, Literal(name)))
        g.add((prop, RDFS.domain, BIM[domain]))
        g.add((prop, RDFS.range, xsd_type))


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------


def generate_tbox(output_path: Path | None = None) -> Path:
    """Generate the TBox OWL file and return its path."""
    if output_path is None:
        output_path = config.ONTOLOGY_OWL
    output_path.parent.mkdir(parents=True, exist_ok=True)

    g = build_tbox()
    g.serialize(destination=str(output_path), format="turtle")
    return output_path
