from functools import wraps
from pathlib import Path
from typing import Callable, Optional

from rdflib.graph import Graph, Store, plugin

from buildingmotif.namespaces import bind_prefixes

PROJECT_DIR = Path(__file__).resolve().parent


def _with_db_open(func: Callable) -> Callable:
    """Decorator that opens and closes database.

    :param func: decorated function
    :type func: Callable
    """

    @wraps(func)
    def wrapper(self, *args):
        self.dataset.open(self.db_uri)
        res = func(self, *args)
        self.dataset.close()

        return res

    return wrapper


class GraphConnection:
    """Manages graph connection."""

    def __init__(
        self,
        db_uri: Optional[str] = None,
        db_identifier: Optional[str] = "buildingmotif_store",
    ) -> None:
        """Creates datastore and database.

        :param db_uri: defaults to None
        :type db_uri: Optional[str], optional
        :param db_identifier: defaults to "buildingmotif_store"
        :type db_identifier: Optional[str], optional
        """
        if db_uri is None:
            db_path = PROJECT_DIR / f"{db_identifier}.db"
            db_uri = f"sqlite:///{db_path}"

        self.db_uri = db_uri

        self.store = plugin.get("SQLAlchemy", Store)(identifier=db_identifier)
        self.store.open(self.db_uri)

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

    def get_all_graph_identifiers(self) -> list[str]:
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
