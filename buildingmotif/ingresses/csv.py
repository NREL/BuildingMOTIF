from csv import DictReader
from functools import cached_property
from pathlib import Path
from typing import Callable, List, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.term import Node

from buildingmotif.dataclasses import Template
from buildingmotif.ingresses.base import IngressHandler, Record


class CSVIngress(IngressHandler):
    """
    Reads rows from a CSV file and exposes them as records.
    The type of the record is the name of the CSV file
    """

    def __init__(self, filename: Path):
        self.filename = filename

    @cached_property
    def records(self) -> Optional[List[Record]]:
        records = []
        rdr = DictReader(open(self.filename))
        for row in rdr:
            rec = Record(
                rtype=str(self.filename),
                fields=row,
            )
            records.append(rec)

        return records

    def graph(self, _ns: Namespace) -> Optional[Graph]:
        return None


# TODO: excel reader


def get_term(field_value: str, ns: Namespace) -> Node:
    try:
        uri = URIRef(ns[field_value])
        uri.n3()  # raises an exception if invalid URI
        return uri
    except Exception:
        return Literal(field_value)


class TemplateIngress(IngressHandler):
    """
    Reads records and attempts to instantiate the given template
    with each record. Produces a graph.

    If 'inline' is True, inlines all templates when they are instantiated.
    """

    def __init__(self, template: Template, upstream: IngressHandler, inline=False):
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
            bindings = {k: get_term(v, ns) for k, v in rec.fields.items()}
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
        upstream: IngressHandler,
        inline=False,
    ):
        self.chooser = chooser
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
            bindings = {k: get_term(v, ns) for k, v in rec.fields.items()}
            graph = template.evaluate(bindings)
            assert isinstance(graph, Graph)
            g += graph
        return g
