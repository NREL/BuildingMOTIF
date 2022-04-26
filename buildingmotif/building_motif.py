from sqlalchemy import create_engine

from buildingmotif.db_connections.graph_connection import GraphConnection
from buildingmotif.db_connections.table_connection import TableConnection
from buildingmotif.singleton import Singleton


class BuildingMotif(metaclass=Singleton):
    """Manages BuildingMOTIF data classes."""

    def __init__(self, db_uri: str) -> None:
        """Class constructor.

        :param db_uri: db uri
        :type db_uri: str
        """
        self.engine = create_engine(db_uri, echo=True)
        self.table_con = TableConnection(self.engine)
        self.graph_con = GraphConnection(self.engine)

    def __del__(self):
        self.engine.dispose()
