from dataclasses import dataclass
from typing import Dict, List, Set

from rdflib import URIRef

from buildingmotif.dataclasses import Library, Template

BrickClass = URIRef  # not specific enough, but it gets the point across


@dataclass(frozen=True, eq=True)
class SegmentedLabel:
    label: str
    identifiers: List[str]


@dataclass(frozen=True, eq=True)
class LabelSet:
    token_classes: List[URIRef]
    segmented_labels: Set[SegmentedLabel]


@dataclass(frozen=True, eq=True)
class Cost:
    edge_cost: float
    params_dropped: int
    tokens_dropped: int

    @property
    def scalar(self):
        return self.edge_cost + self.tokens_dropped #self.params_dropped + self.tokens_dropped


@dataclass(frozen=True, eq=True)
class Token:
    identifier: str
    classname: BrickClass

    @property
    def class_(self):
        return self.classname[self.classname.find("#") + 1 :]

    def __repr__(self):
        return f"{self.identifier} a {self.class_}"


@dataclass(frozen=True, eq=True)
class Param:
    name: str
    classname: BrickClass

    @property
    def class_(self):
        return self.classname[self.classname.find("#") + 1 :]

    def __repr__(self):
        return f"{self.name} a {self.class_}"


@dataclass(frozen=True, eq=True)
class Bindings:
    segmented_label: SegmentedLabel
    template: Template
    bindings: Dict[Param, Token]


@dataclass(frozen=True, eq=True)
class BestLabelSetBindings:
    template: Template
    labelset: LabelSet
    bindings_indices: Dict[
        Param, Token
    ]  # the Token.name is the index of relevant LabelSet.segmented_labels[].identifiers

    def get_bindings_list(self) -> List[Bindings]:
        bindings_list = []

        for segmented_label in self.labelset.segmented_labels:
            token_identifiers = segmented_label.identifiers
            bindings = {
                param: Token(
                    identifier=token_identifiers[token.identifier],
                    classname=token.classname,
                )
                for param, token in self.bindings_indices.items()
            }

            bindings_list.append(
                Bindings(
                    segmented_label=segmented_label,
                    template=self.template,
                    bindings=bindings,
                )
            )

        return bindings_list
