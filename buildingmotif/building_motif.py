from typing import Optional

import rdflib
from rdflib.util import guess_format
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from buildingmotif.dataclasses.template_library import TemplateLibrary
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
        Session = sessionmaker(bind=self.engine, autoflush=True)
        self.session = Session()

        self.table_connection = TableConnection(self.engine, self)
        self.graph_connection = GraphConnection(self.engine, self)

    def load_library(self, ontology_graph: Optional[str] = None) -> None:
        # if ontology graph is provided, then read shapes from it and turn
        # those into templates
        if ontology_graph is not None:
            ontology = rdflib.Graph()
            ontology.parse(ontology_graph, format=guess_format(ontology_graph))
            print(len(ontology))
            lib = TemplateLibrary.from_ontology(ontology)
            # TODO: add deps, etc? Or is this done in the template library constructor?
            print(lib)
        pass

    def close(self) -> None:
        """Close session and engine."""
        self.session.close()
        self.engine.dispose()
