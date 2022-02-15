from pathlib import Path
from typing import Callable, Optional

import rdflib
from rdflib.graph import ConjunctiveGraph, Graph, Store, plugin
from buildingmotif.namespaces import bind_prefixes

PROJECT_DIR = Path(__file__).resolve().parent


def _with_db_open(func: Callable) -> Callable:
    """Decorator that opens and closes db

    :param func: decorated function
    :type func: Callable
    """

    def wrapper(self, *args):
        self.dataset.open(self.db_uri)
        res = func(self, *args)
        self.dataset.close()

        return res

    return wrapper


class GraphHandler:
    def __init__(
        self,
        db_uri: Optional[str] = None,
        db_identifier: Optional[str] = "buildingmotif_store",
    ) -> None:
        """Creates store and db

        :param db_uri: defaults to None
        :type db_uri: Optional[str], optional
        :param db_identifier: defaults to "buildingmotif_store"
        :type db_identifier: Optional[str], optional
        """
        if db_uri is None:
            db_path = PROJECT_DIR / f"{db_identifier}.db"
            db_uri = f"sqlite:///{db_path}"

        self.db_uri = db_uri

        store = plugin.get("SQLAlchemy", Store)(identifier=db_identifier)
        self.dataset = ConjunctiveGraph(store)

        self.dataset.open(self.db_uri, create=True)
        self.dataset.close()

    @_with_db_open
    def create_graph(self, identifier: str, graph: Optional[Graph] = None) -> Graph:
        """Create a graph in the dataset

        :param identifier: identifier of graph
        :type identifier: str
        :param graph: graph to add, defaults to None
        :type graph: Optional[Graph], optional
        :return: graph added
        :rtype: Graph
        """
        new_triples = [(s, o, p, identifier) for (s, o, p) in graph]
        self.dataset.addN(new_triples)

        return graph

    @_with_db_open
    def get_all_graph_identifiers(self) -> list[str]:
        """get all graph identifiers

        :return: all graph identifiers
        :rtype: list[str]
        """
        contexts = self.dataset.contexts()
        context_identifiers = [str(c.identifier) for c in contexts]

        return context_identifiers

    @_with_db_open
    def get_graph(self, identifier: str) -> Graph:
        """get Graph by identifier. Graph has triples, no context

        :param identifier: graph identifier
        :type identifier: str
        :return: graph without context
        :rtype: Graph
        """
        result = Graph()
        bind_prefixes(result)
        for t in self.dataset.get_context(identifier):
            result.add(t)

        return result

    @_with_db_open
    def update_graph(self, identifier: str, update_graph: Graph) -> Graph:
        raise NotImplementedError

    @_with_db_open
    def delete_graph(self, identifier: str) -> None:
        context = rdflib.term.URIRef(identifier)
        self.dataset.remove((None, None, None, context))
