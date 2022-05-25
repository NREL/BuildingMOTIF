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
        """
        Loads a library from the provided source.

        Currently only supports reading in *templates* from an ontology graph,
        but eventually we will want to add other sources.

        :param ontology_graph: ontology graph filename or URL
        :type ontology_graph: str
        """
        # if ontology graph is provided, then read shapes from it and turn
        # those into templates
        if ontology_graph is not None:
            ontology = rdflib.Graph()
            ontology.parse(ontology_graph, format=guess_format(ontology_graph))
            lib = TemplateLibrary.from_ontology(ontology)
            self.session.commit()
            print(
                f"Defined libary {lib.name} with {len(lib.get_templates())} templates"
            )
        else:
            raise Exception("No library information provided")

    def close(self) -> None:
        """Close session and engine."""
        self.session.close()
        self.engine.dispose()
