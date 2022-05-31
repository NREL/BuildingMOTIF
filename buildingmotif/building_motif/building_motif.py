from pathlib import Path
from typing import TYPE_CHECKING, Optional

import rdflib
from rdflib.util import guess_format
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from buildingmotif.building_motif.singleton import (
    Singleton,
    SingletonNotInstantiatedException,
)
from buildingmotif.database.graph_connection import GraphConnection
from buildingmotif.database.table_connection import TableConnection

if TYPE_CHECKING:
    from buildingmotif.dataclasses.template_library import TemplateLibrary


class BuildingMOTIF(metaclass=Singleton):
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

    def load_library(
        self, ontology_graph: Optional[str] = None, directory: Optional[str] = None
    ) -> "TemplateLibrary":
        """
        Loads a library from the provided source.

        Currently only supports reading in *templates* from an ontology graph,
        but eventually we will want to add other sources.

        :param ontology_graph: ontology graph filename or URL
        :type ontology_graph: str

        :param directory: directory containing templates + shapes
        :type directory: str
        """
        # avoids circular import...obviously not ideal but it would be nice
        # to have a unified API surface somewhere so that users don't have to search
        # all over the project in order to find the methods they need
        from buildingmotif.dataclasses.template_library import TemplateLibrary

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
            return lib
        elif directory is not None:
            lib = TemplateLibrary.from_directory(Path(directory))
            self.session.commit()
            print(
                f"Defined libary {lib.name} with {len(lib.get_templates())} templates"
            )
            return lib
        else:
            raise Exception("No library information provided")

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
