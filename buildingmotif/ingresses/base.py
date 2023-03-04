from dataclasses import dataclass
from functools import cached_property
from typing import List

from rdflib import Graph, Namespace

from buildingmotif import BuildingMOTIF


@dataclass
class Record:
    """Represents a piece of metadata from some metadata ingress"""

    # an arbitrary "type hint"
    rtype: str
    # possibly-nested dictionary of (semi-)structured data from
    # the underlying source
    fields: dict


class IngressHandler:
    """Abstract superclass for Record/Graph ingress handlers"""

    pass


class RecordIngressHandler(IngressHandler):
    """Generates Record instances from an underlying metadata source"""

    def __init__(self, bm: BuildingMOTIF):
        self.bm = bm

    @cached_property
    def records(self) -> List[Record]:
        """
        Generates (then caches) a list of Records from an underlying data source
        """
        raise NotImplementedError("Must be overridden by subclass")


class GraphIngressHandler(IngressHandler):
    """Generates a Graph from an underlying metadata source or RecordIngressHandler"""

    def __init__(self, bm: BuildingMOTIF):
        self.bm = bm

    def graph(self, ns: Namespace) -> Graph:
        """Generates an RDF graph with all entities being placed in the given namespace"""
        raise NotImplementedError("Must be overridden by subclass")
