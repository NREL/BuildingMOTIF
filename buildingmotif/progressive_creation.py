from itertools import permutations
from pprint import pprint
from typing import List

from rdflib import Graph

from buildingmotif.dataclasses import Template
from buildingmotif.template_matcher import TemplateMatcher

# from rdflib.compare import graph_diff


def progressive_plan(templates: List[Template], context: Graph) -> List[Template]:
    """
    We are given a list of templates; this is either a set of templates that
    the model author supplies directly or are derived from sets of shapes that
    need to be fulfilled.

    We want to optimize the population of these templates: there may be
    redundant information between them, or there may be some unique/rare parts
    of templates whose populations can be postponed.
    """
    # for pair in combinations(templates, 2):
    for pair in permutations(templates, 2):
        t1, t2 = pair[0].in_memory_copy(), pair[1].in_memory_copy()
        print(t1.body.serialize())
        print("-" * 100)
        print(t2.body.serialize())
        print("-" * 100)
        tm = TemplateMatcher(t1.body, t2, context)
        print(id(tm))
        for mapping, subgraph in tm.building_mapping_subgraphs_iter(
            size=tm.largest_mapping_size
        ):
            print(id(mapping), id(subgraph))
            pprint(mapping)
            print(subgraph.serialize())

        # both, first, second = graph_diff(pair[0].body, pair[1].body)
        # print(both.serialize())
        print("*" * 100)
        print("*" * 100)

    return []
