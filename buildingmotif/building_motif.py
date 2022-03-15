from typing import Optional

import rdflib

from buildingmotif.data_classes import Model
from buildingmotif.db_connections.graph_connection import GraphConnection
from buildingmotif.db_connections.table_connection import TableConnection


class BuildingMotif:
    """Manages BuildingMOTIF data classes."""

    def __init__(self, db_uri: str) -> None:
        """Class constructor.

        :param db_uri: db uri
        :type db_uri: str
        """
        self.table_con = TableConnection(db_uri)
        self.graph_con = GraphConnection(db_uri)

    def create_model(self, name: str, graph: Optional[rdflib.Graph] = None) -> Model:
        """Create model.

        :param name: name
        :type name: str
        :param graph: graph, defaults to None
        :type graph: Optional[rdflib.Graph], optional
        :return: created Model
        :rtype: Model
        """
        db_model = self.table_con.create_db_model(name)

        if graph is None:
            graph = rdflib.Graph()

        new_graph = self.graph_con.create_graph(db_model.graph_id, graph)

        return Model(id=db_model.id, name=db_model.name, graph=new_graph)

    def get_model(self, id: int) -> Model:
        """Get model.

        :param id: id
        :type id: str
        :return: model
        :rtype: Model
        """
        db_model = self.table_con.get_db_model(id)
        graph = self.graph_con.get_graph(db_model.graph_id)

        return Model(id=id, name=db_model.name, graph=graph)

    def save_model(self, model: Model) -> None:
        """Save model to the database.

        :param model: model
        :type model: Model
        """
        db_model = self.table_con.get_db_model(model.id)

        self.table_con.update_db_model_name(db_model.id, model.name)
        self.graph_con.update_graph(db_model.graph_id, model.graph)

    def delete_model(self, model: Model) -> None:
        """Deep delete model.

        :param model: model to delete
        :type model: Model
        """
        db_model = self.table_con.get_db_model(model.id)

        self.graph_con.delete_graph(db_model.graph_id)
        self.table_con.delete_db_model(db_model.id)
