import logging
from typing import List

import numpy as np
from rdflib import Namespace

from buildingmotif.dataclasses import Template
from buildingmotif.semantic_graph_synthesizer.bipartite_token_mapper import (
    BipartiteTokenMapper,
)
from buildingmotif.semantic_graph_synthesizer.classes import (
    Bindings,
    Cost,
    LabelSet,
    Token,
    TokenizedLabel,
)

BLDG = Namespace("urn:building/")


logger = logging.getLogger()


def default_cost_loss_function(cost: Cost) -> float:
    return cost.scalar


class SemanticGraphSynthesizer:
    def __init__(
        self,
        bindings_cost_threshold=np.inf,
        cost_loss_function=default_cost_loss_function,
        should_inline_dependencies=True,
    ):
        self.bindings_cost_threshold = bindings_cost_threshold
        self.cost_loss_function = cost_loss_function
        self.should_inline_dependencies = should_inline_dependencies

    def _group_labels_by_tokens(self, labels: List[TokenizedLabel]) -> List[LabelSet]:
        """ "Group labels into labelsets based on shared sets on token classes"""
        labelsets: List[LabelSet] = []

        for label in labels:
            label.tokens.sort(key=lambda t: t.classname)
            token_classes = [t.classname for t in label.tokens]

            # proper labelset for tokenized_label
            labelset = next(
                (
                    labelset
                    for labelset in labelsets
                    if labelset.token_classes == token_classes
                ),
                None,
            )

            if labelset is None:
                labelset = LabelSet(token_classes=token_classes, labels=[])
                labelsets.append(labelset)

            # append it to the label set
            labelset.labels.append(label)

        return labelsets

    def find_bindings_for_label(
        self, templates: List[Template], label: TokenizedLabel
    ) -> Bindings:
        """Gets the bindings for a specific label."""
        best_bindings = Bindings(
            label=label, template=None, bindings={}, cost=Cost.inf()
        )

        logger.debug("Template costs:")
        for template in templates:
            if self.should_inline_dependencies:
                template = template.inline_dependencies()

            bindings, cost = BipartiteTokenMapper.find_bindings_for_tokens_and_template(
                label.tokens, template
            )
            logger.debug(f"- {template.name} {cost.scalar}")

            if (
                self.cost_loss_function(cost)
                < self.cost_loss_function(best_bindings.cost)
                and self.cost_loss_function(cost) < self.bindings_cost_threshold
            ):
                best_bindings = Bindings(
                    label=label,
                    template=template,
                    bindings=bindings,
                    cost=cost,
                )

        return best_bindings

    def find_bindings_for_labelset(
        self, templates: List[Template], labelset: LabelSet
    ) -> List[Bindings]:
        """Find the bindings a given LabelSet."""
        index_label = TokenizedLabel(
            label="Index Label",
            tokens=[
                Token(identifier=str(i), classname=tc)
                for i, tc in enumerate(labelset.token_classes)
            ],
        )
        index_bindings = self.find_bindings_for_label(templates, index_label)

        bindings_list = []
        for label in labelset.labels:
            token_identifiers = [t.identifier for t in label.tokens]
            bindings = {
                param: Token(
                    identifier=token_identifiers[int(token.identifier)],
                    classname=token.classname,
                )
                for param, token in index_bindings.bindings.items()
            }

            bindings_list.append(
                Bindings(
                    label=label,
                    template=index_bindings.template,
                    bindings=bindings,
                    cost=index_bindings.cost,
                )
            )

        return bindings_list

    def find_bindings_for_labels(
        self, templates: List[Template], labels: List[TokenizedLabel]
    ) -> List[Bindings]:
        """Find the bindings a given labels.

        Groups them in label sets for optimization purposes.
        """
        labelsets = self._group_labels_by_tokens(labels)

        bindings_list = []
        for labelset in labelsets:
            bindings_list.extend(self.find_bindings_for_labelset(templates, labelset))

        return bindings_list
