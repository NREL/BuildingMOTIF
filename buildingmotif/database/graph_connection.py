from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from rdflib.graph import Graph, Store, plugin

if TYPE_CHECKING:
    from buildingmotif.building_motif.building_motif import BuildingMotifEngine
from buildingmotif.namespaces import bind_prefixes

PROJECT_DIR = Path(__file__).resolve().parent


class GraphConnection:
    """Manages graph connection."""

    def __init__(
        self,
        engine: "BuildingMotifEngine",
        db_identifier: Optional[str] = "buildingmotif_store",
    ) -> None:
        """Creates datastore and database.

        :param engine: db engine
        :type engine: Engine
        :param session_manager: contains the session to use
        :type session_manager: BuildingMotif
        :param db_identifier: defaults to "buildingmotif_store"
        :type db_identifier: Optional[str], optional
        """
        self.store = plugin.get("SQLAlchemy", Store)(
            identifier=db_identifier, engine=engine
        )
        self.store.create_all()

    def create_graph(self, identifier: str, graph: Graph) -> Graph:
        """Create a graph in the database.

        :param identifier: identifier of graph
        :type identifier: str
        :param graph: graph to add, defaults to None
        :type graph: Graph
        :return: graph added
        :rtype: Graph
        """
        g = Graph(self.store, identifier=identifier)
        new_triples = [(s, o, p, g) for (s, o, p) in graph]
        g.addN(new_triples)

        return g

    def get_all_graph_identifiers(self) -> List[str]:
        """Get all graph identifiers.

        :return: all graph identifiers
        :rtype: list[str]
        """
        return [str(c) for c in self.store.contexts()]

    def get_graph(self, identifier: str) -> Graph:
        """Get graph by identifier. Graph has triples, no context.

        :param identifier: graph identifier
        :type identifier: str
        :return: graph without context
        :rtype: Graph
        """
        result = Graph(self.store, identifier=identifier)
        bind_prefixes(result)

        return result

    def delete_graph(self, identifier: str) -> None:
        """Delete graph."""
        g = Graph(self.store, identifier=identifier)
        self.store.remove((None, None, None), g)
