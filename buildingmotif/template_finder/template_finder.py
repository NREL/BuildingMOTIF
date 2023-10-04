from typing import Dict, List, Tuple

import numpy as np
from rdflib import URIRef

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Template
from buildingmotif.namespaces import BACNET, BRICK, PARAM
from buildingmotif.template_finder.calculate_cost import (
    calculate_bindings_for_params_and_tokens,
)
from buildingmotif.template_finder.classes import Cost, Param, Token


def get_typed_params(template) -> List[Param]:
    query = """
        SELECT ?s ?o
        WHERE {
            ?s a ?o
            FILTER (strstarts(str(?s), 'urn:___param___'))
        }
    """
    params = []
    for s, c in template.body.query(query):
        params.append(Param(name=s[len(PARAM) :], classname=c))
    return params


def calculate_bindings_for_template_and_tokens(
    tokens: List[Token], template: Template, verbose=False
) -> Tuple[Template, Dict[Param, Token], Cost]:
    params = get_typed_params(template)
    try:
        mapping, cost = calculate_bindings_for_params_and_tokens(
            tokens, params, verbose=verbose
        )
    except ValueError:
        mapping, cost = {}, Cost(
            edge_cost=np.inf, params_dropped=len(params), tokens_dropped=len(tokens)
        )

    return mapping, cost


def calculate_best_bindings_for_template_and_tokens(
    templates: List[Template], tokens: list[Token], verbose=False
):
    best_template = None
    best_mapping = []
    best_cost = Cost(edge_cost=np.inf, params_dropped=0, tokens_dropped=len(tokens))

    if verbose:
        print("Template costs:")
    for template in templates:
        template = template.inline_dependencies()
        mapping, cost = calculate_bindings_for_template_and_tokens(tokens, template, verbose=True)

        if verbose:
            print(f"- {template.name} {cost.scalar}")

        if cost.scalar < best_cost.scalar:
            best_template = template
            best_mapping = mapping
            best_cost = cost

    return best_template, best_mapping, best_cost
