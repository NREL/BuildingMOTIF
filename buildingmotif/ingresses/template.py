from typing import Callable, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.term import Node

from buildingmotif.dataclasses import Template
from buildingmotif.ingresses.base import (
    GraphIngressHandler,
    Record,
    RecordIngressHandler,
)


class TemplateIngress(GraphIngressHandler):
    """
    Reads records and attempts to instantiate the given template
    with each record. Produces a graph.

    If 'inline' is True, inlines all templates when they are instantiated.
    """

    def __init__(
        self,
        template: Template,
        mapper: Optional[Callable[[str], str]],
        upstream: RecordIngressHandler,
        inline: bool = False,
    ):
        """
        Create a new TemplateIngress handler

        :param template: the template to instantiate on each record
        :type template: Template
        :param mapper: Function which takes a column name as input and returns
                       the name of the parameter the corresponding cell should
                       be bound to. If None, uses the column name as the
                       parameter name
        :type mapper: Optional[Callable[[str], str]]
        :param upstream: the ingress handler from which to source records
        :type upstream: RecordIngressHandler
        :param inline: if True, inline the template before evaluating it on
                      each row, defaults to False
        :type inline: bool, optional
        """
        self.mapper = mapper if mapper else lambda x: x
        self.upstream = upstream
        if inline:
            self.template = template.inline_dependencies()
        else:
            self.template = template

    def graph(self, ns: Namespace) -> Graph:
        g = Graph()

        # ensure 'ns' is a Namespace or URI forming won't work
        if not isinstance(ns, Namespace):
            ns = Namespace(ns)

        records = self.upstream.records
        assert records is not None
        for rec in records:
            bindings = {self.mapper(k): _get_term(v, ns) for k, v in rec.fields.items()}
            graph = self.template.evaluate(bindings, require_optional_args=True)
            if not isinstance(graph, Graph):
                bindings, graph = graph.fill(ns, include_optional=True)
            g += graph
        return g


class TemplateIngressWithChooser(GraphIngressHandler):
    """
    Reads records and attempts to instantiate a template with each record.
    Uses a 'chooser' function to determine which template should be
    instantiated for each record. Produces a graph.

    If 'inline' is True, inlines all templates when they are instantiated.
    """

    def __init__(
        self,
        chooser: Callable[[Record], Template],
        mapper: Optional[Callable[[str], str]],
        upstream: RecordIngressHandler,
        inline=False,
    ):
        """
        Create a new TemplateIngress handler

        :param template: the template to instantiate on each record
        :type template: Template
        :param chooser: Function which takes a record and returns the Template
                       which the record should be evaluated on.
        :type mapper: Optional[Callable[[Record], Template]]
        :param mapper: Function which takes a column name as input and returns
                       the name of the parameter the corresponding cell should
                       be bound to. If None, uses the column name as the
                       parameter name
        :type mapper: Optional[Callable[[str], str]]
        :param upstream: the ingress handler from which to source records
        :type upstream: RecordIngressHandler
        :param inline: if True, inline the template before evaluating it on
                      each row, defaults to False
        :type inline: bool, optional
        """
        self.chooser = chooser
        self.mapper = mapper if mapper else lambda x: x
        self.upstream = upstream
        self.inline = inline

    def graph(self, ns: Namespace) -> Graph:
        g = Graph()

        # ensure 'ns' is a Namespace or URI forming won't work
        if not isinstance(ns, Namespace):
            ns = Namespace(ns)

        records = self.upstream.records
        assert records is not None
        for rec in records:
            template = self.chooser(rec)
            if self.inline:
                template = template.inline_dependencies()
            bindings = {self.mapper(k): _get_term(v, ns) for k, v in rec.fields.items()}
            graph = template.evaluate(bindings)
            if not isinstance(graph, Graph):
                _, graph = graph.fill(ns)
            g += graph
        return g


def _get_term(field_value: str, ns: Namespace) -> Node:
    assert isinstance(ns, Namespace), f"{ns} must be a rdflib.Namespace instance"
    try:
        uri = URIRef(ns[field_value])
        uri.n3()  # raises an exception if invalid URI
        return uri
    except Exception:
        return Literal(field_value)
