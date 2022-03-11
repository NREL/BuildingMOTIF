from dataclasses import dataclass

import rdflib


@dataclass
class Model:
    """Model of a building. This class mirrors DBModel."""

    id: str
    name: str
    graph: rdflib.Graph
