from pathlib import Path
from pprint import pprint
from typing import List, Optional

import numpy as np
import pandas as pd
from rdflib import Graph, URIRef
from scipy.optimize import linear_sum_assignment

from buildingmotif.namespaces import BRICK

BrickClass = URIRef  # not specific enough, but it gets the point across

brick = Graph()
PROJECT_DIR = Path(__file__).resolve().parents[1]
brick.parse(PROJECT_DIR / "libraries/brick/Brick.ttl")


def get_parent_class(brick_class: BrickClass) -> Optional[BrickClass]:
    """Get the immediate parent of brick class"""
    query = """
        SELECT ?parent
        WHERE {{
            ?child rdfs:subClassOf ?parent
        }}
    """
    result = brick.query(query, initBindings={"child": brick_class})
    parents = (parent for (parent,) in result)

    return next(parents, None)


def get_edge_cost(
    token_class: BrickClass, param_class: BrickClass, cost_power: Optional[int] = 0
) -> float:
    """
    Return the cost between brick classes token_class and param_class where cost is:

     - inf if token_class is not covariant of param_class.
     - 2 to the power of the number of hops between the classes.
    """
    if token_class == param_class:
        return 2**cost_power

    parent_class = get_parent_class(token_class)
    if parent_class is None:
        return np.inf

    return get_edge_cost(parent_class, param_class, cost_power + 1)


def create_cost_matrix(
    token_classes: List[BrickClass], param_classes: List[BrickClass]
) -> pd.DataFrame:
    """Create cost matrix of the above classes."""
    cost_matrix = pd.DataFrame(
        index=param_classes,
        columns=token_classes,
    )

    for token_class in cost_matrix.columns:
        for param_class, _ in cost_matrix[token_class].items():
            cost_matrix.loc[param_class, token_class] = get_edge_cost(
                token_class, param_class
            )

    print("\ncost matrix:")
    pprint(
        cost_matrix.rename(
            columns=lambda x: x[x.find("#") + 1 :],
            index=lambda x: x[x.find("#") + 1 :],
        )
    )
    return cost_matrix


def calculate_cost(
    token_classes: List[BrickClass], param_classes: List[BrickClass]
) -> float:
    """Get the cost of mapping token_classes to param_classes."""
    cost_matrix = create_cost_matrix(token_classes, param_classes)
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    kept_costs = list(zip(row_ind, col_ind))

    print("\nkept edges:")
    for x, y in kept_costs:
        token = cost_matrix.index[x]
        param = cost_matrix.columns[y]
        print(
            f"{token[token.find('#')+1:]} <- {cost_matrix.iloc[x, y]} -> {param[param.find('#')+1:]}"
        )

    return {
        "edge_cost": cost_matrix.to_numpy()[row_ind, col_ind].sum(),
        "params_dropped": len(param_classes) - len(kept_costs),
        "tokens_dropped": len(token_classes) - len(kept_costs),
    }
