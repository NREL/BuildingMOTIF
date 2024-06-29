import logging
import os
from typing import Optional

from pytest import MonkeyPatch
from rdflib import Graph
from rdflib.namespace import NamespaceManager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import buildingmotif
import buildingmotif.building_motif.building_motif
import buildingmotif.building_motif.singleton
from buildingmotif.building_motif.building_motif import BuildingMotifEngine
from buildingmotif.database.graph_connection import GraphConnection
from buildingmotif.database.table_connection import TableConnection
from buildingmotif.database.tables import Base as BuildingMOTIFBase
from buildingmotif.database.utils import (
    _custom_json_deserializer,
    _custom_json_serializer,
)
from buildingmotif.namespaces import bind_prefixes

# The fact that BuildingMOTIF is a singleton class is a problem for testing templates.
# We want to have tests which are parameterized by the library and template name; this makes
# it possible to use pytest filters (with the "-k" flag) to run tests for specific libraries or templates.
# We want each (library, template) pair to operate in a "clean" environment, so that the tests are isolated.
# However, the singleton pattern means that the BuildingMOTIF instance is shared across all tests.
# We can work around this by patching BuildingMOTIF to ignore the singleton pattern.

# "instances" is a dictionary that maps the name of the module to the BuildingMOTIF instance.
instances = {}


# non-singleton BuildingMOTIF
class BuildingMOTIF:
    """Manages BuildingMOTIF data classes."""

    def __init__(
        self,
        db_uri: str,
        shacl_engine: Optional[str] = "pyshacl",
        log_level=logging.WARNING,
    ) -> None:
        """Class constructor.

        :param db_uri: database URI
        :type db_uri: str
        :param shacl_engine: the name of the engine to use for validation: "pyshacl" or "topquadrant". Using topquadrant
            requires Java to be installed on this machine, and the "topquadrant" feature on BuildingMOTIF,
            defaults to "pyshacl"
        :type shacl_engine: str, optional
        :param log_level: logging level of detail
        :type log_level: int
        :default log_level: INFO
        """
        self.db_uri = db_uri
        self.shacl_engine = shacl_engine
        self.engine = create_engine(
            db_uri,
            echo=False,
            json_serializer=_custom_json_serializer,
            json_deserializer=_custom_json_deserializer,
        )
        self.session_factory = sessionmaker(bind=self.engine, autoflush=True)
        self.Session = scoped_session(self.session_factory)

        self.setup_logging(log_level)

        # setup tables automatically if using a in-memory sqlite database
        if self._is_in_memory_sqlite():
            self.setup_tables()

        self.table_connection = TableConnection(self.engine, self)
        self.graph_connection = GraphConnection(
            BuildingMotifEngine(self.engine, self.Session)
        )

        g = Graph()
        bind_prefixes(g)
        self.template_ns_mgr: NamespaceManager = NamespaceManager(g)

    @property
    def session(self):
        return self.Session()

    def setup_tables(self):
        """Creates all tables in the underlying database."""
        BuildingMOTIFBase.metadata.create_all(self.engine)

    def _is_in_memory_sqlite(self) -> bool:
        """Returns true if the BuildingMOTIF instance uses an in-memory SQLite
        database.
        """
        if self.engine.dialect.name != "sqlite":
            return False
        # get the 'filename' of the database; if this is empty, the db is in-memory
        raw_conn = self.engine.raw_connection()
        filename = (
            raw_conn.cursor()
            .execute("select file from pragma_database_list where name='main';", ())
            .fetchone()
        )
        # length is 0 if the db is in-memory
        return not len(filename[0])

    def setup_logging(self, log_level):
        """Create log file with DEBUG level and stdout handler with specified
        logging level.

        :param log_level: logging level of detail
        :type log_level: int
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s |  %(levelname)s: %(message)s"
        )

        log_file_handler = logging.FileHandler(
            os.path.join(os.getcwd(), "BuildingMOTIF.log"), mode="w"
        )
        log_file_handler.setLevel(logging.DEBUG)
        log_file_handler.setFormatter(formatter)

        engine_logger = logging.getLogger("sqlalchemy.engine")
        pool_logger = logging.getLogger("sqlalchemy.pool")

        engine_logger.setLevel(logging.WARN)
        pool_logger.setLevel(logging.WARN)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(formatter)

        root_logger.addHandler(log_file_handler)
        root_logger.addHandler(stream_handler)

    def close(self) -> None:
        """Close session and engine."""
        self.session.close()
        self.engine.dispose()


# The normal get_building_motif method uses the fact that BuildingMOTIF is a singleton class.
# We need to mock this method so that we can create a new instance of BuildingMOTIF for each test.
# We use the "instances" dictionary to store the BuildingMOTIF instance for each module.
# If the instance does not exist, we create a new one and store it in the dictionary.
# TODO: how to handle testing different shacl_engines?
def mock_building_motif():
    global instances
    from buildingmotif import BuildingMOTIF

    name = os.environ["bmotif_module"]
    if name not in instances:
        instances[name] = BuildingMOTIF("sqlite://", shacl_engine="topquadrant")
        instances[name].setup_tables()
    return instances[name]


# This is a context ("with PatchBuildingMotif()") that patches the "get_building_motif" method
# to use the correct BuildingMOTIF instance for each test. We have to patch the get_building_motif
class PatchBuildingMotif:
    def __enter__(self):
        self.monkeypatch = MonkeyPatch()
        self.monkeypatch.setattr(
            buildingmotif.dataclasses.library, "get_building_motif", mock_building_motif
        )
        self.monkeypatch.setattr(
            buildingmotif.dataclasses.model, "get_building_motif", mock_building_motif
        )
        self.monkeypatch.setattr(
            buildingmotif.dataclasses.shape_collection,
            "get_building_motif",
            mock_building_motif,
        )
        self.monkeypatch.setattr(
            buildingmotif.dataclasses.template,
            "get_building_motif",
            mock_building_motif,
        )
        self.monkeypatch.setattr(
            buildingmotif.building_motif.building_motif,
            "get_building_motif",
            mock_building_motif,
        )
        self.monkeypatch.setattr(
            buildingmotif, "get_building_motif", mock_building_motif
        )
        return self.monkeypatch

    def __exit__(self, *args):
        self.monkeypatch.undo()
