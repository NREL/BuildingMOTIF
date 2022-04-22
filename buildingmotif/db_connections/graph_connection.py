from pathlib import Path
from typing import Optional

import rdflib
from rdflib.graph import ConjunctiveGraph, Graph, Store, plugin
from sqlalchemy.engine import Engine

from buildingmotif.namespaces import bind_prefixes

PROJECT_DIR = Path(__file__).resolve().parent


class GraphConnection:
    """Manages graph connection."""

    def __init__(
        self,
        engine: Engine,
        db_identifier: Optional[str] = "buildingmotif_store",
    ) -> None:
        """Creates datastore and database.

        :param engine: db engine
        :type engine: Engine
        :param db_identifier: defaults to "buildingmotif_store"
        :type db_identifier: Optional[str], optional
        """
        store = plugin.get("SQLAlchemy", Store)(engine=engine, identifier=db_identifier)
        store.create_all()
        self.dataset = ConjunctiveGraph(store)

    def create_graph(self, identifier: str, graph: Graph) -> Graph:
        """Create a graph in the database.

        :param identifier: identifier of graph
        :type identifier: str
        :param graph: graph to add, defaults to None
        :type graph: Graph
        :return: graph added
        :rtype: Graph
        """
        new_triples = [(s, o, p, identifier) for (s, o, p) in graph]
        self.dataset.addN(new_triples)

        return graph

    def get_all_graph_identifiers(self) -> list[str]:
        """Get all graph identifiers.

        :return: all graph identifiers
        :rtype: list[str]
        """
        contexts = self.dataset.contexts()
        context_identifiers = [str(c.identifier) for c in contexts]

        return context_identifiers

    def get_graph(self, identifier: str) -> Graph:
        """Get graph by identifier. Graph has triples, no context.

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

    def update_graph(self, identifier: str, update_graph: Graph) -> Graph:
        """Update graph.

        :param identifier: id of graph
        :type identifier: str
        :param update_graph: new graph
        :type update_graph: Graph
        :return: new graph
        :rtype: Graph
        """
        self.dataset.remove((None, None, None, identifier))

        new_triples = [(s, o, p, identifier) for (s, o, p) in update_graph]
        self.dataset.addN(new_triples)

        return update_graph

    def delete_graph(self, identifier: str) -> None:
        """Delete graph."""
        context = rdflib.term.URIRef(identifier)
        self.dataset.remove((None, None, None, context))
