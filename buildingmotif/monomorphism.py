"""
Using the VF2 algorithm to compute subgraph isomorphisms between a template T and a graph G.
If the found isomorphism is a subgraph of T, then T is not fully matched and additional
input is required to fully populate the template.
"""
from collections import defaultdict
from collections.abc import Callable
from itertools import combinations
from typing import Dict, Generator, List, Set

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
) -> "TemplateMonomorphisms":
    """
    Returns the set of subgraphs of G that are monomorphic to T; these are organized
    by how "complete" the monomorphism is.

    TODO: fix it! Make a new class that can hold and organize the results.
    """
    # saves all of the mappings we have seen, organized by how big the mapping is
    ret = TemplateMonomorphisms(G, T)
    for Tsubgraph in generate_all_template_subgraphs(T):
        assert Tsubgraph is not None
        matching = VF2SemanticMatcher(G, Tsubgraph, ontology)
        if matching.subgraph_is_monomorphic():
            for sg in matching.subgraph_monomorphisms_iter():
                ret.add_mapping(sg)
    return ret


class TemplateMonomorphisms:
    """
    A class that holds the results of the template matching process.
    """

    mappings: Dict[int, List[Dict[Node, Node]]] = defaultdict(list)
    template: Graph
    building: Graph

    def __init__(self, building: Graph, template: Graph):
        self.template = template
        self.building = building

    def add_mapping(self, mapping: Dict[Node, Node]):
        """
        Adds a mapping to the set of mappings.
        """
        if mapping not in self.mappings[len(mapping)]:
            self.mappings[len(mapping)].append(mapping)

    @property
    def largest_mapping_size(self) -> int:
        """
        Returns the size of the largest mapping
        """
        return max(self.mappings.keys())

    def mappings_of_size(self, size: int) -> List[Dict[Node, Node]]:
        """
        Returns the mappings of the given size
        """
        return self.mappings[size]

    def subgraph_from_mapping(self, mapping: Dict[Node, Node]) -> Graph:
        """
        Returns the subgraph of the building graph that corresponds to the given
        mapping.
        """
        g = rdflib_to_networkx_digraph(self.building)
        sg = g.subgraph(list(mapping.keys()))
        return digraph_to_rdflib(sg)

    def mappings_iter(self) -> Generator[Dict[Node, Node], None, None]:
        """
        Returns an iterator over all of the mappings in descending order
        of the size of the mapping. This means the most complete mappings
        will be returned first.
        """
        for size in sorted(self.mappings.keys(), reverse=True):
            for mapping in self.mappings_of_size(size):
                if not mapping:
                    continue
                yield mapping

    def subgraphs_iter(self) -> Generator[Graph, None, None]:
        """
        Returns an iterator over all of the subgraphs in descending order
        of the size of the subgraph. This means the most complete subgraphs
        will be returned first.
        """
        for size in sorted(self.mappings.keys(), reverse=True):
            for mapping in self.mappings_of_size(size):
                if not mapping:
                    continue
                yield self.subgraph_from_mapping(mapping)
