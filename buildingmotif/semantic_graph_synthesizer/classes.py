from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from rdflib import URIRef

from buildingmotif.dataclasses import Template


@dataclass
class Cost:
    edge_cost: float
    params_dropped: int
    tokens_dropped: int

    @property
    def scalar(self):
        return (
            self.edge_cost + self.tokens_dropped
        )  # self.params_dropped + self.tokens_dropped

    @classmethod
    def inf(self):
        return Cost(edge_cost=np.inf, params_dropped=np.inf, tokens_dropped=np.inf)


@dataclass
class Param:
    name: URIRef
    classname: URIRef

    @property
    def class_(self):
        return self.classname[self.classname.find("#") + 1 :]

    def __repr__(self):
        return f"{self.name} a {self.class_}"


@dataclass
class Token:
    identifier: str
    classname: URIRef

    @property
    def class_(self):
        return self.classname[self.classname.find("#") + 1 :]

    def __repr__(self):
        return f"{self.identifier} (type {self.classname})"


@dataclass
class TokenizedLabel:
    label: str
    tokens: list[Token]

    @staticmethod
    def from_dict(d):
        return TokenizedLabel(
            label=d["label"],
            tokens=[
                Token(identifier=t["identifier"], classname=URIRef(t["type"]))
                for t in d["tokens"]
            ],
        )

    def __repr__(self):
        r = ""
        for token in self.tokens:
            r += f"    - {token}\n"

        return f"{self.label}:\n{r}"


@dataclass
class LabelSet:
    token_classes: List[URIRef]
    labels: List[TokenizedLabel]


@dataclass
class Bindings:
    label: TokenizedLabel
    template: Optional[Template]
    bindings: Dict[URIRef, Token]
    cost: Cost


@dataclass
class UnifiedBindings:
    labels: List[TokenizedLabel]
    template: Template
    bindings: Dict[str, Token]
    cost: Cost
