"""
Using the VF2 algorithm to compute subgraph isomorphisms between a template T and a graph G.
If the found isomorphism is a subgraph of T, then T is not fully matched and additional
input is required to fully populate the template.
"""
from collections.abc import Callable
from itertools import combinations
from typing import Dict, Generator, Set, Tuple

import networkx as nx
from networkx.algorithms.isomorphism import DiGraphMatcher
from rdflib import Graph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
from rdflib.term import Node

from buildingmotif.namespaces import OWL, RDF, RDFS


def _get_types(n: Node, g: Graph) -> Set[Node]:
    return set(g.objects(n, RDF.type))


def _compatible_types(
    n1: Node, g1: Graph, n2: Node, g2: Graph, ontology: Graph
) -> bool:
    for n1type in _get_types(n1, g1):
        for n2type in _get_types(n2, g2):
            if n2type in ontology.transitive_objects(
                n1type, RDFS.subClassOf
            ) or n1type in ontology.transitive_objects(n2type, RDFS.subClassOf):
                return True
    return False


def get_semantic_feasibility(
    G1: Graph, G2: Graph, ontology: Graph
) -> Callable[[Node, Node], bool]:
    """
    Returns a function that checks if two nodes are semantically feasible to be
    matched given the information in the provided ontology.

    The function returns true if the two nodes are semantically feasible to be matched.
    We use the following checks:
    1. if the two nodes are both classes, then one must be a subclass of the other
    2. if the two nodes are instances, then they must be of the same class
    TODO: other checks?
    """

    def semantic_feasibility(n1: Node, n2: Node) -> bool:
        # case 0: same node
        if n1 == n2:
            return True
        # case 1: both are classes
        if (n1, RDF.type, OWL.Class) in ontology and (
            n2,
            RDF.type,
            OWL.Class,
        ) in ontology:
            if n2 in ontology.transitive_objects(n1, RDFS.subClassOf):
                return True
            elif n1 in ontology.transitive_objects(n2, RDFS.subClassOf):
                return True
            else:
                return False
        # case 2: both are instances
        if _compatible_types(n1, G1, n2, G2, ontology):
            return True
        return False

    return semantic_feasibility


class VF2SemanticMatcher(DiGraphMatcher):
    """
    A subclass of DiGraphMatcher that incorporates semantic feasibility into the matching
    process using the provided ontology.

    :param T: The template graph
    :param G: The building graph
    :param ontology: The ontology that contains the information about node semantics
    """

    def __init__(self, T: Graph, G: Graph, ontology: Graph):
        super().__init__(rdflib_to_networkx_digraph(T), rdflib_to_networkx_digraph(G))
        self.ontology = ontology
        self._semantic_feasibility = get_semantic_feasibility(T, G, ontology)

    def semantic_feasibility(self, g1: Node, g2: Node) -> bool:
        """
        Returns true if the two nodes are semantically feasible to be matched
        """
        return self._semantic_feasibility(g1, g2)


def generate_all_template_subgraphs(T: Graph) -> Generator[Graph, None, None]:
    """
    Generates all node-induced subgraphs of T in order of decreasing size
    """
    for nodecount in reversed(range(len(T.all_nodes()))):
        for nodelist in combinations(T.all_nodes(), nodecount):
            # print(nodelist)
            yield digraph_to_rdflib(rdflib_to_networkx_digraph(T).subgraph(nodelist))


def digraph_to_rdflib(digraph: nx.DiGraph) -> Graph:
    """
    Turns a nx.DiGraph into an rdflib.Graph. Expects the nx.DiGraph to have been
    produced by rdflib_to_networkx_digraph.
    """
    g = Graph()
    for s, o, pdict in digraph.edges(data=True):
        g.add((s, pdict["triples"][0][1], o))
    return g


def find_largest_subgraph_monomorphism(
    T: Graph, G: Graph, ontology: Graph
) -> Tuple[Dict[Node, Node], Graph]:
    """
    Returns the largest subgraph of T that is monomorphic to G.
    """
    largest_mapping: Dict[Node, Node] = {}
    largest_subgraph = Graph()
    for Tsubgraph in generate_all_template_subgraphs(T):
        assert Tsubgraph is not None
        if len(Tsubgraph) < len(largest_subgraph):
            continue
        matching = VF2SemanticMatcher(G, Tsubgraph, ontology)
        if matching.subgraph_is_monomorphic():
            for sg in matching.subgraph_monomorphisms_iter():
                if len(sg) >= len(largest_mapping):
                    # print(Tsubgraph.serialize(format="turtle"))
                    largest_mapping = sg
                    largest_subgraph = Tsubgraph
    return largest_mapping, largest_subgraph
