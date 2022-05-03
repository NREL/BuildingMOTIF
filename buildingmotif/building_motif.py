from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
        self.db_uri = db_uri
        self.engine = create_engine(db_uri, echo=False)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.table_con = TableConnection(self.engine, self)
        self.graph_con = GraphConnection(self.engine, self)

    def release(self):
        self.session.close()
        self.engine.dispose()
