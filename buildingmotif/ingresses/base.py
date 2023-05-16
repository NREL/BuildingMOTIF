import json
from dataclasses import dataclass
from functools import cached_property
from os import PathLike
from pathlib import Path
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

    def dump(self, path: PathLike):
        output_string = self.dumps()
        Path(path).write_text(output_string)

    def dumps(self) -> str:
        records = [
            {"rtype": record.rtype, "fields": record.fields} for record in self.records
        ]
        return json.dumps(records)

    @classmethod
    def load(cls, path: PathLike):
        return cls.loads(Path(path).read_text())

    @classmethod
    def loads(cls, s: str):
        self = cls.__new__(cls)
        records = []
        for record in json.loads(s):
            records.append(Record(record["rtype"], record["fields"]))
        self.records = records
        return self


class GraphIngressHandler(IngressHandler):
    """Generates a Graph from an underlying metadata source or RecordIngressHandler"""

    def __init__(self, bm: BuildingMOTIF):
        self.bm = bm

    def graph(self, ns: Namespace) -> Graph:
        """Generates an RDF graph with all entities being placed in the given namespace"""
        raise NotImplementedError("Must be overridden by subclass")
