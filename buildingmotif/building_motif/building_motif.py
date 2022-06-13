import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from buildingmotif.building_motif.singleton import (
    Singleton,
    SingletonNotInstantiatedException,
)
from buildingmotif.database.graph_connection import GraphConnection
from buildingmotif.database.table_connection import TableConnection


class BuildingMOTIF(metaclass=Singleton):
    """Manages BuildingMOTIF data classes."""

    def __init__(self, db_uri: str, debug=False) -> None:
        """Class constructor.

        :param db_uri: db uri
        :type db_uri: str

        :param debug: Whether to print debug messages
        :type debug: boolean
        """
        self.db_uri = db_uri
        self.engine = create_engine(db_uri, echo=False)
        Session = sessionmaker(bind=self.engine, autoflush=True)
        self.session = Session()

        self.table_connection = TableConnection(self.engine, self)
        self.graph_connection = GraphConnection(
            BuildingMotifEngine(self.engine, self.session)
        )

        if debug:
            logging.basicConfig(level=logging.DEBUG)

    def close(self) -> None:
        """Close session and engine."""
        self.session.close()
        self.engine.dispose()


def get_building_motif() -> "BuildingMOTIF":
    """Returns singleton instance of BuildingMOTIF.
    Requires that BuildingMOTIF has been instantiated before,
    otherwise an exception will be thrown."""
    if hasattr(BuildingMOTIF, "instance"):
        return BuildingMOTIF.instance  # type: ignore
    raise SingletonNotInstantiatedException


class BuildingMotifEngine:
    """BuildingMotifEngine is a class which wraps a SQLAlchemy Session and Engine.
    This enables the use of sessioned transactions in rdflib-sqlalchemy.
    If we are experiencing weird graph database issues this may be the root"""

    def __init__(self, engine, session) -> None:
        self.engine = engine
        self.session = session

    # begin and connect attributes are queried from the wrapped session.

    @contextmanager
    def begin(self):
        yield self.session

    @contextmanager
    def connect(self):
        yield self.session

    def __getattr__(self, attr):
        # When an attribute is requested, see if we have overriden it
        # If we have not return the attr of the wrapped engine
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self.engine, attr)
