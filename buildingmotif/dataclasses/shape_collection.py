import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Set

import rdflib
from rdflib import RDF, RDFS, URIRef

from buildingmotif import get_building_motif
from buildingmotif.namespaces import BMOTIF, OWL
from buildingmotif.utils import Triple, copy_graph

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF

ONTOLOGY_FILE = (
    Path(__file__).resolve().parents[1] / "resources" / "building_motif_ontology.ttl"
)
ontology = rdflib.Graph().parse(ONTOLOGY_FILE)


@dataclass
class ShapeCollection:
    """This class mirrors :py:class:`database.tables.DBShapeCollection`."""

    _id: int
    graph: rdflib.Graph
    _bm: "BuildingMOTIF"

    @classmethod
    def create(cls) -> "ShapeCollection":
        """Create a new ShapeCollection.

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
        """Get ShapeCollection from database by id.

        :param id: ShapeCollection id
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
        """Add the given triples to the graph.

        :param triples: a sequence of triples to add to the graph
        :type triples: Triple
        """
        for triple in triples:
            self.graph.add(triple)

    def add_graph(self, graph: rdflib.Graph) -> None:
        """Add the given graph to the ShapeCollection.

        :param graph: the graph to add to the ShapeCollection
        :type graph: rdflib.Graph
        """
        self.graph += graph

    def _cbd(self, shape_name, self_contained=True):
        """Retrieves the Concise Bounded Description (CBD) of the shape."""
        cbd = self.graph.cbd(shape_name)
        # if computing self-contained, do the fixed-point computation produced by unioning
        # the CBDs of all nodes in the current CBD until the graph does not change
        changed = True
        while self_contained and changed:
            new_g = rdflib.Graph()
            for node in cbd.all_nodes():
                new_g += self.graph.cbd(node)
            new_cbd = new_g + cbd
            changed = len(new_cbd) > cbd
            cbd = new_cbd
        return cbd

    def resolve_imports(self, recursive_limit: int = -1) -> "ShapeCollection":
        """Resolves `owl:imports` to as many levels as requested.

        By default, all `owl:imports` are recursively resolved. This limit can
        be changed to 0 to suppress resolving imports, or to 1..n to handle
        recursion up to that limit.

        :param recursive_limit: how many levels of `owl:imports` to resolve,
            defaults to -1 (all)
        :type recursive_limit: int, optional
        :return: a new ShapeCollection with the types resolved
        :rtype: ShapeCollection
        """
        resolved_namespaces: Set[rdflib.URIRef] = set()
        resolved = _resolve_imports(self.graph, recursive_limit, resolved_namespaces)
        new_sc = ShapeCollection.create()
        new_sc.add_graph(resolved)
        return new_sc

    @classmethod
    def _get_subclasses_of_definition_type(
        cls, definition_type: URIRef
    ) -> List[URIRef]:
        """Get all the definition types in the ontology that are subclasses in
        the given definition types.

        :param definition_type: the given definition type
        :type definition_type: URIRef
        :return: list of included definition types
        :rtype: List[URIRef]
        """
        children = ontology.subjects(RDFS.subClassOf, definition_type)

        results = [definition_type]
        for child in children:
            results += cls._get_subclasses_of_definition_type(child)

        return results

    @classmethod
    def _get_included_domains(cls, domain: URIRef) -> List[URIRef]:
        """Get all the domains in the ontology that are included in the given
        domains.

        :param domain: the given domain
        :type domain: URIRef
        :return: list of included domains
        :rtype: List[URIRef]
        """
        children = ontology.subjects(BMOTIF.includes, domain)

        results = [domain]
        for child in children:
            results += cls._get_included_domains(child)

        return results

    def get_shapes_of_definition_type(self, definition_type: URIRef) -> List[URIRef]:
        """Get subjects present in shape of the definition type.

        :param definition_type: desired definition type
        :type definition_type: URIRef
        :return: subjects
        :rtype: List[URIRef]
        """
        definition_types = self._get_subclasses_of_definition_type(definition_type)

        results = []
        for definition_type in definition_types:
            results += self.graph.subjects(RDF.type, definition_type)

        return results

    def get_shapes_of_domain(self, domain: URIRef) -> List[URIRef]:
        """Get subjects present in shape of domain type.

        :param domain: desired domain
        :type domain: URIRef
        :return: subjects
        :rtype: List[URIRef]
        """
        included_domains = self._get_included_domains(domain)

        results = []
        for domain in included_domains:
            results += self.graph.subjects(RDF.type, domain)

        return results

    def get_shapes_about_class(
        self, rdf_type: URIRef, contexts: Optional[List["ShapeCollection"]] = None
    ) -> List[URIRef]:
        """Returns a list of shapes that either target the given class (or
        superclasses of it), or otherwise only apply to URIs of the given type.

        :param rdf_type: an OWL class
        :type rdf_type: URIRef
        :param contexts: list of ShapeCollections that help determine the class
            structure
        :type contexts: List["ShapeCollection"], optional
        :return: a list of shapes in this ShapeCollection that concern that
            class
        :rtype: List[URIRef]
        """
        # merge the contexts together w/ our graph if they are provided, else
        # just use the existing shape collection graph
        if contexts is not None:
            context = sum(map(lambda x: x.graph, contexts), rdflib.Graph())
            graph = self.graph + context
        else:
            graph = self.graph
        rows = graph.query(
            f"""
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            SELECT ?shape WHERE {{
            ?shape a sh:NodeShape .
            {rdf_type.n3()} rdfs:subClassOf* ?class .
            {{ ?shape sh:targetClass ?class }}
            UNION
            {{ ?shape sh:class ?class }}
        }}"""
        )
        return [row[0] for row in rows]  # type: ignore


def _resolve_imports(
    graph: rdflib.Graph, recursive_limit: int, seen: Set[rdflib.URIRef]
) -> rdflib.Graph:
    from buildingmotif.dataclasses.library import Library

    logger = logging.getLogger(__name__)

    if recursive_limit == 0:
        return graph
    new_g = copy_graph(graph)
    for ontology in graph.objects(predicate=OWL.imports):
        if ontology in seen:
            continue
        seen.add(ontology)

        # go find the graph definition from our libraries
        try:
            lib = Library.load(name=ontology)
        except Exception as e:
            logger.error(
                "Could not resolve import of library/shape collection: %s", ontology
            )
            raise e
        dependency = _resolve_imports(
            lib.get_shape_collection().graph, recursive_limit - 1, seen
        )
        new_g += dependency
        print(f"graph size now {len(new_g)}")
    return new_g
