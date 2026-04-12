"""RDF namespace constants for the BIM ontology.

URI scheme inherits from the existing ``spatial_relationships.ttl`` produced by
DXTnavis, extended with additional namespaces for the ontology layer.
"""

from rdflib import Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD  # noqa: F401 — re-export

BIM = Namespace("http://example.org/bim-ontology/")
INST = Namespace("http://example.org/bim-ontology/instance/")
SPATIAL = Namespace("http://example.org/bim-ontology/spatial/")

NAMESPACE_BINDINGS: dict[str, Namespace] = {
    "bim": BIM,
    "inst": INST,
    "spatial": SPATIAL,
    "owl": OWL,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
}
