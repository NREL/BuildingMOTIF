from collections import Counter
from typing import Callable, Dict, List

from rdflib import Graph

from buildingmotif.dataclasses import Template
from buildingmotif.template_matcher import (
    _ontology_lookup_cache,
    get_semantic_feasibility,
)
from buildingmotif.utils import Term, Triple

# from rdflib.compare import graph_diff


def compatible_triples(
    a: Triple, b: Triple, sf_func: Callable[[Term, Term], bool]
) -> bool:
    """
    Two triples are compatible if:
    - they are the same
    - they are pairwise semantically feasible
    """
    if a == b:
        return True
    for (a_term, b_term) in zip(a, b):
        if not sf_func(a_term, b_term):
            return False
    return True


def progressive_plan(templates: List[Template], context: Graph) -> List[Template]:
    """
    We are given a list of templates; this is either a set of templates that
    the model author supplies directly or are derived from sets of shapes that
    need to be fulfilled.

    We want to optimize the population of these templates: there may be
    redundant information between them, or there may be some unique/rare parts
    of templates whose populations can be postponed.
    """
    # present result as a sequence of (parameterized) triples?

    # greedy algorithm:
    # start with the most common (substitutable) triple amongst all templates
    # then choose the next most common triple, and so on.
    # Yield triples that have parameters; automatically include
    # non-parameterized triples
    templates = [template.inline_dependencies() for template in templates]
    histogram: Counter = Counter()

    inv: Dict[Triple, Template] = {}

    for templ in templates:
        cache = _ontology_lookup_cache()
        for body_triple in templ.body.triples((None, None, None)):
            found = False
            for hist_triple in histogram.keys():
                sf_func = get_semantic_feasibility(
                    templ.body, inv[hist_triple].body, context, cache
                )
                if compatible_triples(body_triple, hist_triple, sf_func):
                    print(body_triple)
                    print(hist_triple)
                    print("-" * 50)
                    found = True
                    histogram[hist_triple] += 1
                    break
            if not found:
                histogram[body_triple] = 1
                inv[body_triple] = templ

    from pprint import pprint

    pprint(histogram)

    most_common = histogram.most_common()
    # start with most common triple
    seed = most_common.pop(0)
    print(seed[0])

    # now to search outwards. We want to generate a sequence of triples
    # that maximizes the number of templates that are included in the resulting graph.
    # This is analogous to creating a left-biased CDF of (original) templates included

    # idea 1: just iterate through most common histogram
    # This has no guarantee that the sequence is optimal *or* connected.
    # We probably want to prioritize creating a connected sequence..
    for triple in most_common:
        print(triple[0])

    # TODO: need to mark when a new template is satisfied
    # can look at the CDF for a site specification as part of paper evaluation

    # stub of an alternative approach...
    # for pair in combinations(templates, 2):
    # for pair in permutations(templates, 2):
    #    t1, t2 = pair[0].in_memory_copy(), pair[1].in_memory_copy()
    #    print(t1.body.serialize())
    #    print("-" * 100)
    #    print(t2.body.serialize())
    #    print("-" * 100)
    #    tm = TemplateMatcher(t1.body, t2, context)
    #    for mapping, subgraph in tm.building_mapping_subgraphs_iter(
    #        size=tm.largest_mapping_size
    #    ):
    #        pprint(mapping)
    #        print(subgraph.serialize())

    #    # both, first, second = graph_diff(pair[0].body, pair[1].body)
    #    # print(both.serialize())
    #    print("*" * 100)
    #    print("*" * 100)

    return []
