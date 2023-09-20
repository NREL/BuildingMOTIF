from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from typing import List, Optional

import numpy as np
import pandas as pd
from rdflib import Graph, URIRef
from scipy.optimize import linear_sum_assignment

BrickClass = URIRef  # not specific enough, but it gets the point across

brick = Graph()
PROJECT_DIR = Path(__file__).resolve().parents[1]
brick.parse(PROJECT_DIR / "libraries/brick/Brick.ttl")


@dataclass(frozen=True, eq=True)
class Token:
    identifier: str
    classname: BrickClass

    @property
    def class_(self):
        return self.classname[self.classname.find("#") + 1 :]


@dataclass(frozen=True, eq=True)
class Param:
    name: str
    classname: BrickClass

    @property
    def class_(self):
        return self.classname[self.classname.find("#") + 1 :]


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
        return 2**cost_power - 1

    parent_class = get_parent_class(token_class)
    if parent_class is None:
        return np.inf

    return get_edge_cost(parent_class, param_class, cost_power + 1)


def create_cost_matrix(
    tokens: List[Token], params: List[Param], verbose=False
) -> pd.DataFrame:
    """Create cost matrix of the above classes."""
    cost_matrix = pd.DataFrame(
        index=params,
        columns=tokens,
    )

    for i, token in enumerate(cost_matrix.columns):
        for j, param in enumerate(cost_matrix.index):
            cost_matrix.iloc[j, i] = get_edge_cost(token.classname, param.classname)

    if verbose:
        print("cost matrix:")
        pprint(
            cost_matrix.rename(
                columns=lambda x: x.class_,
                index=lambda x: x.class_,
            )
        )
    return cost_matrix


def calculate_cost(tokens: List[Token], params: List[Param], verbose=False) -> dict:
    """Get the cost of mapping token_classes to param_classes."""
    cost_matrix = create_cost_matrix(tokens, params, verbose=verbose)
    # # uncomment / comment for v different results.
    cost_matrix = (
        cost_matrix.replace(np.inf, np.nan)
        .dropna(axis=0, how="all")
        .replace(np.nan, np.inf)
    )
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    kept_costs = list(zip(row_ind, col_ind))

    print("\nkept edges:")
    for token_idx, param_idx in kept_costs:
        token = cost_matrix.index[token_idx]
        param = cost_matrix.columns[param_idx]
        print(
            f"{token.class_} <- {cost_matrix.iloc[token_idx, param_idx]} -> {param.class_}"
        )
    # maps parameter indices to token indices
    mapping = {cost_matrix.index[x]: cost_matrix.columns[y] for x, y in kept_costs}

    # if the 1st dimension of the cost_matrix is 0 then we have dropped all of the parameters
    # and the cost is infinite
    edge_cost = (
        cost_matrix.to_numpy()[row_ind, col_ind].sum()
        if cost_matrix.shape[0] > 0
        else float("inf")
    )
    return {
        "mapping": mapping,
        "edge_cost": edge_cost,
        "params_dropped": len(params) - len(kept_costs),
        "tokens_dropped": len(tokens) - len(kept_costs),
    }
