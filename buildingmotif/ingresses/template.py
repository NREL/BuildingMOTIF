from functools import cached_property
from typing import Callable, List, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.term import Node

from buildingmotif.dataclasses import Template
from buildingmotif.ingresses.base import IngressHandler, Record


class TemplateIngress(IngressHandler):
    """
    Reads records and attempts to instantiate the given template
    with each record. Produces a graph.

    If 'inline' is True, inlines all templates when they are instantiated.
    """

    def __init__(
        self,
        template: Template,
        mapper: Optional[Callable[[str], str]],
        upstream: IngressHandler,
        inline=False,
    ):
        self.mapper = mapper if mapper else lambda x: x
        self.upstream = upstream
        if inline:
            self.template = template.inline_dependencies()
        else:
            self.template = template

    @cached_property
    def records(self) -> Optional[List[Record]]:
        return None

    def graph(self, ns: Namespace) -> Optional[Graph]:
        g = Graph()

        records = self.upstream.records
        assert records is not None
        for rec in records:
            bindings = {self.mapper(k): get_term(v, ns) for k, v in rec.fields.items()}
            graph = self.template.evaluate(bindings)
            assert isinstance(graph, Graph)
            g += graph
        return g


class TemplateIngressWithChooser(IngressHandler):
    """
    Reads records and attempts to instantiate the given template
    with each record. Produces a graph.

    If 'inline' is True, inlines all templates when they are instantiated.
    """

    def __init__(
        self,
        chooser: Callable[[Record], Template],
        mapper: Optional[Callable[[str], str]],
        upstream: IngressHandler,
        inline=False,
    ):
        self.chooser = chooser
        self.mapper = mapper if mapper else lambda x: x
        self.upstream = upstream
        self.inline = inline

    @cached_property
    def records(self) -> Optional[List[Record]]:
        return None

    def graph(self, ns: Namespace) -> Optional[Graph]:
        g = Graph()

        records = self.upstream.records
        assert records is not None
        for rec in records:
            template = self.chooser(rec)
            if self.inline:
                template = template.inline_dependencies()
            bindings = {self.mapper(k): get_term(v, ns) for k, v in rec.fields.items()}
            graph = template.evaluate(bindings)
            assert isinstance(graph, Graph)
            g += graph
        return g


def get_term(field_value: str, ns: Namespace) -> Node:
    try:
        uri = URIRef(ns[field_value])
        uri.n3()  # raises an exception if invalid URI
        return uri
    except Exception:
        return Literal(field_value)
