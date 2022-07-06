from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

import pyshacl
import rdflib

from buildingmotif import get_building_motif
from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.utils import Triple, copy_graph

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF


@dataclass
class Model:
    """Model. This class mirrors DBModel."""

    _id: int
    _name: str
    graph: rdflib.Graph
    _bm: "BuildingMOTIF"

    @classmethod
    def create(cls, name: str) -> "Model":
        """create new Model

        :param name: new model name
        :type name: str
        :return: new Model
        :rtype: Model
        """
        bm = get_building_motif()
        db_model = bm.table_connection.create_db_model(name)
        g = rdflib.Graph()
        g.add((rdflib.URIRef(name), rdflib.RDF.type, rdflib.OWL.Ontology))
        graph = bm.graph_connection.create_graph(db_model.graph_id, g)

        return cls(_id=db_model.id, _name=db_model.name, graph=graph, _bm=bm)

    @classmethod
    def load(cls, id: int) -> "Model":
        """Get Model from db by id

        :param id: model id
        :type id: int
        :return: Model
        :rtype: Model
        """
        bm = get_building_motif()
        db_model = bm.table_connection.get_db_model(id)
        graph = bm.graph_connection.get_graph(db_model.graph_id)

        return cls(_id=db_model.id, _name=db_model.name, graph=graph, _bm=bm)

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, new_id):
        raise AttributeError("Cannot modify db id")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name: str):
        self._bm.table_connection.update_db_model_name(self._id, new_name)
        self._name = new_name

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
        Add the given graph to the model

        :param graph: the graph to add to the model
        :type graph: rdflib.Graph
        """
        self.graph += graph

    def validate(self, shape_collections: List[ShapeCollection]) -> bool:
        """
        Validates this model against the given shape collections. Loads all of the shape_collections
        into a single graph.

        TODO: determine the return types; At least a bool for valid/invalid, but also want
         a report. Is this the base pySHACL report? Or a useful transformation, like a list
         of deltas for potential fixes?

        :param shape_collections: a list of shape_collections against which the
                                  graph should be validated
        :type shape_collections: List[ShapeCollection]
        :return: True if the model passes validation, false otherwise
        :rtype: bool
        """
        shapeg = rdflib.Graph()
        for sc in shape_collections:
            shapeg += sc.graph
        # TODO: do we want to preserve the materialized triples added to data_graph via reasoning?
        data_graph = copy_graph(self.graph)
        valid, _, report = pyshacl.validate(
            data_graph, shacl_graph=shapeg, advanced=True, js=True, allow_warnings=True
        )
        print(report)
        return valid
