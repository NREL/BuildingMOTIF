from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import rdflib
from rdflib import RDF, RDFS, URIRef

from buildingmotif import get_building_motif
from buildingmotif.namespaces import BMOTIF
from buildingmotif.utils import Triple

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF

ONTOLOGY_FILE = (
    Path(__file__).resolve().parents[1] / "resources" / "building_motif_ontology.ttl"
)
ontology = rdflib.Graph().parse(ONTOLOGY_FILE)


@dataclass
class ShapeCollection:
    """ShapeCollection. This class mirrors DBShapeCollection."""

    _id: int
    graph: rdflib.Graph
    _bm: "BuildingMOTIF"

    @classmethod
    def create(cls) -> "ShapeCollection":
        """create new ShapeCollection

        :return: new ShapeCollection
        :rtype: ShapeCollection
        """
        bm = get_building_motif()
        db_shape_collection = bm.table_connection.create_db_shape_collection()
        graph = bm.graph_connection.create_graph(
            db_shape_collection.graph_id, rdflib.Graph()
        )

        return cls(_id=db_shape_collection.id, graph=graph, _bm=bm)

    @classmethod
    def load(cls, id: int) -> "ShapeCollection":
        """Get ShapeCollection from db by id

        :param id: shape collection id
        :type id: int
        :return: ShapeCollection
        :rtype: ShapeCollection
        """
        bm = get_building_motif()
        db_shape_collection = bm.table_connection.get_db_shape_collection(id)
        graph = bm.graph_connection.get_graph(db_shape_collection.graph_id)

        return cls(_id=db_shape_collection.id, graph=graph, _bm=bm)

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, new_id):
        raise AttributeError("Cannot modify db id")

    def add_triples(self, *triples: Triple) -> None:
        """
        Add the given triples to the graph

        :param triples: a sequence of triples to add to the graph
        :type triples: Triple
        """
        for triple in triples:
            self.graph.add(triple)

    def add_graph(self, graph: rdflib.Graph) -> None:
        """
        Add the given graph to the shape collection

        :param graph: the graph to add to the shape collection
        :type graph: rdflib.Graph
        """
        self.graph += graph

    @classmethod
    def _get_subclasses_of_definition_type(
        cls, definition_type: URIRef
    ) -> List[URIRef]:
        """get all the definition_types in the ontology that are subclasses
             in the given definition_types.

        :param definition_type: the given definition_type
        :type definition_type: URIRef
        :return: list of includes definition_types
        :rtype: list[URIRef]
        """
        children = ontology.subjects(RDFS.subClassOf, definition_type)

        results = [definition_type]
        for child in children:
            results += cls._get_subclasses_of_definition_type(child)

        return results

    @classmethod
    def _get_included_domains(cls, domain: URIRef) -> List[URIRef]:
        """get all the domains in the ontology that are included in the given domains.

        :param domain: the given domain
        :type domain: URIRef
        :return: list of includes domains
        :rtype: list[URIRef]
        """
        children = ontology.subjects(BMOTIF.includes, domain)

        results = [domain]
        for child in children:
            results += cls._get_included_domains(child)

        return results

    def get_shapes_of_definition_type(self, definition_type: URIRef) -> List[URIRef]:
        """get subjects present in shape of definition_type

        :param definition_type: desired definition_type
        :type definition_type: URIRef
        :return: subjects
        :rtype: list[URIRef]
        """
        definition_types = self._get_subclasses_of_definition_type(definition_type)

        results = []
        for definition_type in definition_types:
            results += self.graph.subjects(RDF.type, definition_type)

        return results

    def get_shapes_of_domain(self, domain: URIRef) -> List[URIRef]:
        """get subjects present in shape of domain type

        :param domain: desired domain
        :type domain: URIRef
        :return: subjects
        :rtype: list[URIRef]
        """
        included_domains = self._get_included_domains(domain)

        results = []
        for domain in included_domains:
            results += self.graph.subjects(RDF.type, domain)

        return results
