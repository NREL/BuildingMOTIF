from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generator, List, Optional, Set

import pyshacl
import rdflib
from rdflib import RDF, RDFS, URIRef

from buildingmotif import get_building_motif
from buildingmotif.namespaces import BMOTIF, OWL, SH, A
from buildingmotif.utils import Triple, copy_graph, replace_nodes

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

    def _cbd(self, shape_name, self_contained=True):
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

    def get_shape(self, name: rdflib.URIRef) -> "Shape":
        return Shape(name, self._cbd(name, self_contained=True))

    def get_shapes(self, self_contained: bool = True) -> Generator["Shape", None, None]:
        """
        Yields a sequence of the Concise Bounded Description of the shapes in this shape
        collection. The CBD may refer to other definitions in the enclosing shape graph. If
        we are planning on using a shape somewhere else (for instance, to create a Library of
        requirements for a particular site), then we will want the CBDs to be *self-contained*.

        The self_contained flag uses a fixed-point computation to produce CBDs that are fully
        self-contained.


        :param self_contained: produce CBDs that are fully self-contained, defaults to True
        :type self_contained: bool, optional
        :return: sequence of shapes
        :rtype: Generator[rdflib.Graph, None, None]
        """
        shapes = self.graph.query(
            """SELECT DISTINCT ?shape WHERE {
            ?shape a sh:NodeShape .
            FILTER (!isBlank(?shape)) }"""
        )
        for (shape_name,) in shapes:  # type: ignore
            yield Shape(
                shape_name, self._cbd(shape_name, self_contained=self_contained)
            )

    def get_class_shapes(
        self, self_contained: bool = True
    ) -> Generator["Shape", None, None]:
        """
        Yields a sequence of all named (not blank node) shapes in this
        shape collection that are ALSO owl:Class. See ::ShapeCollection.get_shapes:: for
        more information on computing the CBD.

        :param self_contained: produce CBDs that are fully self-contained, defaults to True
        :type self_contained: bool, optional
        :return: sequence of shapes
        :rtype: Generator[rdflib.Graph, None, None]
        """
        shapes = self.graph.query(
            """SELECT DISTINCT ?shape WHERE {
            ?shape a sh:NodeShape, owl:Class .
            FILTER (!isBlank(?shape)) }"""
        )
        for (shape_name,) in shapes:  # type: ignore
            yield Shape(
                shape_name, self._cbd(shape_name, self_contained=self_contained)
            )

    def resolve_imports(self, recursive_limit: int = -1) -> "ShapeCollection":
        """
        Returns a new ShapeCollection with `owl:imports` resolved to as many levels
        as requested. By default, all `owl:imports` are recursively resolved. This limit
        can be changed to 0 to suppress resolving imports, or to 1..n to handle recursion
        up to that limit

        :param recursive_limit: How many levels of owl:imports to resolve, defaults to -1 (all)
        :type recursive_limit: int, optional
        :return: a new ShapeCollection with the types resolved
        :rtype: "ShapeCollection"
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

    def get_shapes_about_class(self, rdf_type: URIRef) -> List[URIRef]:
        """
        Returns a list of shapes that either target the given class, or otherwise only
        apply to URIs of the given type

        :param rdf_type: an OWL class
        :type rdf_type: URIRef
        :return: A list of shapes in this collection that concern that class
        :rtype: List[URIRef]
        """
        rows = self.graph.query(
            f"""SELECT ?shape WHERE {{
            ?shape a sh:NodeShape .
            {{ ?shape sh:targetClass {rdf_type.n3()} }}
            UNION
            {{ ?shape sh:class {rdf_type.n3()} }}
        }}"""
        )
        return [row[0] for row in rows]  # type: ignore


@dataclass
class Shape:
    """Holds application requirements, etc"""

    name: rdflib.URIRef
    graph: rdflib.Graph

    def __repr__(self) -> str:
        return f"Shape<{self.name}, {len(self.graph)} triples>"

    def dump(self) -> str:
        return self.graph.serialize()

    def get_satisfying_templates(self):
        """
        Searches BuildingMOTIF for any templates that satisfy this shape
        TODO: does not work
        """
        from buildingmotif.dataclasses import Template

        bm = get_building_motif()
        TMP = rdflib.Namespace("urn:tmp/")
        for _templ in bm.table_connection.get_all_db_templates():
            templ = Template.load(_templ.id)
            bindings, body = templ.fill(TMP)
            g = body + self.graph
            g.add((bindings["name"], A, self.name))
            valid, _, _ = pyshacl.validate(data_graph=g, advanced=True)
            if valid:
                print(f"Satisfied by {templ.name}")
            print(g.serialize())
            break

    def copy(self, new_name: rdflib.URIRef) -> "Shape":
        """
        Creates a new copy of this Shape with a new name
        """
        new_g = copy_graph(self.graph)
        replace_nodes(new_g, {self.name: new_name})
        return Shape(new_name, new_g)

    def with_cardinality(self, cardinality: int) -> "Shape":
        """
        Returns a new shape that requires 'cardinality' instances
        of this shape/class in a given graph.

        Requires the https://nrel.gov/BuildingMOTIF/constraints ontology
        """
        new_name = self.name + f"_constraint_{cardinality}"
        NS = rdflib.Namespace("https://nrel.gov/BuildingMOTIF/constraints#")
        shape = self.copy(new_name)
        shape.graph.add((shape.name, A, SH.NodeShape))
        shape.graph.add((shape.name, SH.targetClass, OWL.Ontology))
        shape.graph.add((shape.name, NS["exactCount"], rdflib.Literal(cardinality)))
        shape.graph.add((shape.name, NS["node"], self.name))
        # TODO: need shape to assert as instance?
        rule = rdflib.BNode()
        shape.graph.add((shape.name, SH.rule, rule))
        shape.graph.add((rule, SH.condition, self.name))
        shape.graph.add((rule, A, SH.TripleRule))
        shape.graph.add((rule, SH.subject, SH.this))
        shape.graph.add((rule, SH.predicate, A))
        shape.graph.add((rule, SH.object, self.name))

        return shape


def _resolve_imports(
    graph: rdflib.Graph, recursive_limit: int, seen: Set[rdflib.URIRef]
) -> rdflib.Graph:
    from buildingmotif.dataclasses.library import Library

    if recursive_limit == 0:
        return graph
    new_g = copy_graph(graph)
    for ontology in graph.objects(predicate=OWL.imports):
        if ontology in seen:
            continue
        seen.add(ontology)

        # go find the graph definition from our libraries
        lib = Library.load(name=ontology)
        dependency = _resolve_imports(
            lib.get_shape_collection().graph, recursive_limit - 1, seen
        )
        new_g += dependency
        print(f"graph size now {len(new_g)}")
    return new_g
