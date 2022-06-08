from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import rdflib

from buildingmotif import get_building_motif
from buildingmotif.utils import Triple

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF


@dataclass
class Shape:
    """Shape. This class mirrors DBShape."""

    _id: int
    graph: rdflib.Graph
    _bm: "BuildingMOTIF"

    @classmethod
    def create(cls) -> "Shape":
        """create new Shape

        :return: new Shape
        :rtype: Shape
        """
        bm = get_building_motif()
        db_shape = bm.table_connection.create_db_shape()
        graph = bm.graph_connection.create_graph(db_shape.graph_id, rdflib.Graph())

        return cls(_id=db_shape.id, graph=graph, _bm=bm)

    @classmethod
    def load(cls, id: int) -> "Shape":
        """Get Shape from db by id

        :param id: shape id
        :type id: int
        :return: Shape
        :rtype: Shape
        """
        bm = get_building_motif()
        db_shape = bm.table_connection.get_db_shape(id)
        graph = bm.graph_connection.get_graph(db_shape.graph_id)

        return cls(_id=db_shape.id, graph=graph, _bm=bm)

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
        Add the given graph to the shape

        :param graph: the graph to add to the shape
        :type graph: rdflib.Graph
        """
        self.graph += graph
