import logging
from typing import Callable, Optional

from rdflib import BNode, Graph, Literal, Namespace, URIRef
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
        fill_unused: bool = False,
        inline: bool = False,
        require_optional_args: bool = True,
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
        :param require_optional_args: if True, require that optional arguments in the
                      chosen template be provided by the upstream ingress handler,
                      defaults to False
        :type require_optional_args: bool, optional
        :param fill_unused: if True, mint URIs for any unbound parameters in
                      the template for each input from the upstream ingress handler,
                      defaults to False
        :type fill_unused: bool, optional
        """
        self.mapper = mapper if mapper else lambda x: x
        self.upstream = upstream
        self.require_optional_args = require_optional_args
        if inline:
            self.template = template.inline_dependencies()
        else:
            self.template = template
        self.fill_unused = fill_unused

    def graph(self, ns: Namespace) -> Graph:
        g = Graph()

        # ensure 'ns' is a Namespace or URI forming won't work
        if not isinstance(ns, Namespace):
            ns = Namespace(ns)

        records = self.upstream.records
        assert records is not None
        for rec in records:
            bindings = {self.mapper(k): _get_term(v, ns) for k, v in rec.fields.items()}
            graph = self.template.evaluate(
                bindings, require_optional_args=self.require_optional_args
            )
            # if it is a graph then all expected params were provided and we are done!
            if isinstance(graph, Graph):
                g += graph
                continue
            # here, we know that the 'graph' variable is actually a Template. If fill_unused
            # is True, we use 'fill' on the template to generate a new graph
            if self.fill_unused:
                _, graph = graph.fill(ns, include_optional=self.require_optional_args)
                g += graph
                continue
            raise Exception(f"Paramaters {graph.parameters} are still unused!")
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
        require_optional_args: bool = True,
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
        :param require_optional_args: if True, require that optional arguments in the
                      chosen template be provided by the upstream ingress handler,
                      defaults to False
        :type require_optional_args: bool, optional
        """
        self.chooser = chooser
        self.mapper = mapper if mapper else lambda x: x
        self.upstream = upstream
        self.inline = inline
        self.require_optional_args = require_optional_args

    def graph(self, ns: Namespace) -> Graph:
        g = Graph()

        # ensure 'ns' is a Namespace or URI forming won't work
        if not isinstance(ns, Namespace):
            ns = Namespace(ns)

        records = self.upstream.records
        assert records is not None
        for rec in records:
            template = self.chooser(rec)
            if template is None:
                logging.warning(f"Chooser function does not give a template for {rec}")
                continue
            if self.inline:
                template = template.inline_dependencies()
            bindings = {self.mapper(k): _get_term(v, ns) for k, v in rec.fields.items()}
            graph = template.evaluate(
                bindings, require_optional_args=self.require_optional_args
            )
            if not isinstance(graph, Graph):
                _, graph = graph.fill(ns)
            g += graph
        return g


def _get_term(field_value: str, ns: Namespace) -> Node:
    assert isinstance(ns, Namespace), f"{ns} must be a rdflib.Namespace instance"
    if isinstance(field_value, (URIRef, Literal, BNode)):
        return field_value
    try:
        uri = URIRef(ns[field_value])
        uri.n3()  # raises an exception if invalid URI
        return uri
    except Exception:
        return Literal(field_value)
