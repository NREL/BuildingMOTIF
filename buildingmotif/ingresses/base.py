from dataclasses import dataclass
from functools import cached_property
from typing import List, Optional

from rdflib import Graph, Namespace

from buildingmotif import BuildingMOTIF


@dataclass
class Record:
    """
    Represents a piece of metadata from some metadata ingress
    """

    rtype: str
    fields: dict


class IngressHandler:
    def __init__(self, bm: BuildingMOTIF):
        self.bm = bm

    @cached_property
    def records(self) -> Optional[List[Record]]:
        raise NotImplementedError("Must be overridden by subclass")

    def graph(self, ns: Namespace) -> Optional[Graph]:
        raise NotImplementedError("Must be overridden by subclass")
