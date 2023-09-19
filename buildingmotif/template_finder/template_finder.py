from typing import List

import numpy as np
from rdflib import URIRef

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Template
from buildingmotif.namespaces import BACNET, BRICK
from buildingmotif.template_finder.calculate_cost import calculate_cost

BrickClass = URIRef  # not specific enough, but it gets the point across


def get_templates_param_classes(template):
    query = """
        SELECT ?o
        WHERE {
            ?s a ?o
            FILTER (strstarts(str(?s), 'urn:___param___'))
        }
    """
    param_classes = [c for (c,) in template.body.query(query)]

    return param_classes


def calculate_template_cost(
    token_classes: List[BrickClass], template: Template
) -> float:
    param_classes = get_templates_param_classes(template)

    try:
        cost = calculate_cost(token_classes, param_classes)
    except ValueError:
        cost = np.inf

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
