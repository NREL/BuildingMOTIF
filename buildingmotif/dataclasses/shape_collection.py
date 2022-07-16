from dataclasses import dataclass
from typing import TYPE_CHECKING, Generator, Optional, Set

import rdflib

from buildingmotif import get_building_motif
from buildingmotif.utils import Triple, copy_graph

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF


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
        assert resolved_namespaces
        resolved = copy_graph(self.graph)
        new_sc = ShapeCollection.create()
        new_sc.add_graph(resolved)
        if recursive_limit == 0:
            return new_sc
        return new_sc


@dataclass
class Shape:
    """Holds application requirements, etc"""

    name: rdflib.URIRef
    graph: rdflib.Graph

    def __repr__(self) -> str:
        return f"Shape<{self.name}, {len(self.graph)} triples>"

    def dump(self) -> str:
        return self.graph.serialize()
