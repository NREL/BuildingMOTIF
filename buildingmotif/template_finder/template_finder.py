from typing import List

import numpy as np
from rdflib import URIRef

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Template
from buildingmotif.namespaces import BACNET, BRICK, PARAM
from buildingmotif.template_finder.calculate_cost import Param, Token, calculate_cost

BrickClass = URIRef  # not specific enough, but it gets the point across


def get_templates_param_classes(template):
    query = """
        SELECT ?o
        WHERE {
            ?s a ?o
            FILTER (strstarts(str(?s), 'urn:___param___'))
        }
    """
    param_classes = sorted([c for (c,) in template.body.query(query)])

    return param_classes


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


def calculate_template_cost(
    tokens: List[Token], template: Template, verbose=False
) -> float:
    params = get_typed_params(template)
    try:
        cost = calculate_cost(tokens, params, verbose=verbose)
    except ValueError:
        cost = {"edge_cost": np.inf, "mapping": {}}

    return cost


if __name__ == "__main__":
    bm = BuildingMOTIF("sqlite://")
    pointlist = Library.load(directory="../../libraries/pointlist-test")

    tstat_template = pointlist.get_template_by_name("tstat")
    token_classes = [
        BRICK.Thermostat,
        BRICK.Zone_Air_Temperature_Setpoint,
        BRICK.Occupancy_Sensor,
        BRICK.Zone_Air_Temperature_Sensor,
        BACNET.BACnetDevice,
        BRICK.Mode_Status,
        BRICK.Mode_Command,
    ]

    cost = calculate_template_cost(token_classes, tstat_template)
    print(f"\ncost: {cost}")
