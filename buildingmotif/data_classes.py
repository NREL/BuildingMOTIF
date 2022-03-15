from dataclasses import dataclass
from typing import Optional

import rdflib


@dataclass
class Model:
    """Model of a building. This class mirrors DBModel."""

    id: int
    name: Optional[str]
    graph: rdflib.Graph
