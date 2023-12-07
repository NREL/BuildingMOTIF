from typing import List, Union

from rdflib import Namespace

from buildingmotif.dataclasses import Model, Template
from buildingmotif.semantic_graph_synthesizer.classes import Bindings, UnifiedBindings

BLDG = Namespace("urn:building/")


def unify_bindings(bindings_list: List[Bindings]) -> List[UnifiedBindings]:
    """
    Combine all the bindings for the same template with the same name.
    """
    unified_bindings_list: List[UnifiedBindings] = []
    for bindings in bindings_list:
        if bindings.template is None:
            continue

        unified_bindings = next(
            (
                unified_bindings
                for unified_bindings in unified_bindings_list
                if unified_bindings.template.name == bindings.template.name
                and unified_bindings.bindings["name"] == bindings.bindings["name"]
            ),
            None,
        )

        if unified_bindings is None:
            unified_bindings = UnifiedBindings(
                labels=[],
                template=bindings.template,
                bindings={},
                cost=bindings.cost,
            )
            unified_bindings_list.append(unified_bindings)

        unified_bindings.labels.append(bindings.label)
        unified_bindings.bindings.update(bindings.bindings)

    return unified_bindings_list


def evaluate_bindings(
    bindings: Union[Bindings, UnifiedBindings]
) -> Union[Template, Model]:
    """evaluate bindings"""
    if bindings.template is None:
        raise ValueError("bindings have no template.")

    return bindings.template.evaluate(
        {p: BLDG[t.identifier] for p, t in bindings.bindings.items()}
    )
