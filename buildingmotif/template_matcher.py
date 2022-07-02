"""
Using the VF2 algorithm to compute subgraph isomorphisms between a template T and a graph G.
If the found isomorphism is a subgraph of T, then T is not fully matched and additional
input is required to fully populate the template.
"""
from collections import defaultdict
from itertools import combinations, permutations
from typing import Callable, Dict, Generator, List, Optional, Set, Tuple

import networkx as nx  # type: ignore
from networkx.algorithms.isomorphism import DiGraphMatcher  # type: ignore
from rdflib import Graph, Namespace, URIRef
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph

from buildingmotif.dataclasses import Template
from buildingmotif.namespaces import OWL, PARAM, RDF, RDFS
from buildingmotif.utils import Term, copy_graph

Mapping = Dict[Term, Term]
_MARK = Namespace("urn:__MARK__/")


def _get_types(n: Term, g: Graph) -> Set[URIRef]:
    """
    Types for a node should only be URIRefs, so the
    type filtering here should be safe.
    Defaults to owl:NamedIndividual as a "root" type
    """
    return set(x for x in g.objects(n, RDF.type) if isinstance(x, URIRef)) or {
        OWL.NamedIndividual
    }


def _compatible_types(
    n1: Term, g1: Graph, n2: Term, g2: Graph, ontology: Graph
) -> bool:
    """
    Returns true if the two terms have covariant types.

    :param n1: First node
    :type n1: Term
    :param g1: The graph containing the first node's types
    :type g1: Graph
    :param n2: Second node
    :type n2: Term
    :param g2: The graph containing the second node's types
    :type g2: Graph
    :param ontology: The ontology graph that defines the class hierarchy
    :type ontology: Graph
    :return: True if the nodes are semantically compatible, false otherwise
    :rtype: bool
    """
    for n1type in _get_types(n1, g1):
        for n2type in _get_types(n2, g2):
            if n2type in ontology.transitive_objects(
                n1type, RDFS.subClassOf
            ) or n1type in ontology.transitive_objects(n2type, RDFS.subClassOf):
                return True
    return False


def get_semantic_feasibility(
    G1: Graph, G2: Graph, ontology: Graph
) -> Callable[[Term, Term], bool]:
    """
    Returns a function that checks if two nodes are semantically feasible to be
    matched given the information in the provided ontology.

    The function returns true if the two nodes are semantically feasible to be matched.
    We use the following checks:
    1. If the two nodes are both classes, then one must be a subclass of the other.
    2. If the two nodes are instances, then they must be of the same class.
    TODO: other checks?
    """

    def semantic_feasibility(n1: Term, n2: Term) -> bool:
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


class _VF2SemanticMatcher(DiGraphMatcher):
    """
    A subclass of DiGraphMatcher that incorporates semantic feasibility into the matching
    process using the provided ontology.

    :param T: template graph
    :param G: building graph
    :param ontology: ontology that contains the information about node semantics
    """

    def __init__(self, T: Graph, G: Graph, ontology: Graph):
        super().__init__(rdflib_to_networkx_digraph(T), rdflib_to_networkx_digraph(G))
        self.ontology = ontology
        self._semantic_feasibility = get_semantic_feasibility(T, G, ontology)

    def semantic_feasibility(self, g1: Term, g2: Term) -> bool:
        """
        Returns true if the two nodes are semantically feasible to be matched.
        """
        val = self._semantic_feasibility(g1, g2)
        return val


def generate_all_subgraphs(T: Graph) -> Generator[Graph, None, None]:
    """
    Generates all node-induced subgraphs of T in order of decreasing size.
    """
    for nodecount in reversed(range(len(T.all_nodes()) - 1, len(T.all_nodes()))):
        for nodelist in combinations(T.all_nodes(), nodecount):
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


class TemplateMatcher:
    """
    Computes the set of subgraphs of G that are monomorphic to T; these are organized
    by how "complete" the monomorphism is.
    """

    mappings: Dict[int, List[Mapping]] = defaultdict(list)
    template: Template
    building: Graph
    template_bindings: Dict[str, Term] = {}
    template_graph: Graph

    def __init__(self, building: Graph, template: Template, ontology: Graph):
        self.template = template
        self.building = building
        self.ontology = ontology

        # create an RDF graph from the template that we can use to compute
        # monomorphisms
        # self.template_bindings, self.template_graph = template.fill(_MARK)
        # head_nodes = [
        #    node
        #    for param, node in self.template_bindings.items()
        #    if param in template.head
        # ]
        self.template_graph = copy_graph(template.body)
        self.template_parameters = {PARAM[p] for p in self.template.parameters}

        for template_subgraph in generate_all_subgraphs(self.template_graph):
            matching = _VF2SemanticMatcher(
                self.building, template_subgraph, self.ontology
            )
            if matching.subgraph_is_monomorphic():
                for sg in matching.subgraph_monomorphisms_iter():
                    # sg is a mapping from building graph nodes to template nodes
                    # that constitutes a monomorphism.
                    if len(sg) == 0:
                        continue
                    # TODO: Limit mappings to those that include all of the params?
                    # TODO: ignore optional parameters?
                    # TODO: require that 'name' is in the parameters?

                    # if there is an overlap, yield the subgraph
                    if set(sg.values()).intersection(self.template_parameters):
                        self.add_mapping(sg)

    def add_mapping(self, mapping: Mapping):
        """
        Adds a mapping to the set of mappings.
        """
        if mapping not in self.mappings[len(mapping)]:
            self.mappings[len(mapping)].append(mapping)

    @property
    def largest_mapping_size(self) -> int:
        """
        Returns the size of the largest mapping.
        """
        return max(self.mappings.keys())

    def building_subgraph_from_mapping(self, mapping: Mapping) -> Graph:
        """
        Returns the subgraph of the building graph that corresponds to the given
        mapping.
        """
        g = rdflib_to_networkx_digraph(self.building)
        edges = permutations(mapping.keys(), 2)
        sg = g.edge_subgraph(edges)
        return digraph_to_rdflib(sg)

    def template_subgraph_from_mapping(self, mapping: Mapping) -> Graph:
        """
        Returns the subgraph of the template graph that corresponds to the given
        mapping.
        TODO: need to keep the edges that are more generic than what we have inside the graph.
        For example, if the building has (x a brick:AHU) then we don't need to remind them to
        add an edge (x a brick:Equipment) because that is redundant
        """
        g = rdflib_to_networkx_digraph(self.template_graph)
        return digraph_to_rdflib(g.subgraph(mapping.values()))

    def remaining_template_graph(self, mapping: Mapping) -> Graph:
        """
        Returns the part of the template that is remaining to be filled out given
        a mapping.
        """
        sg = self.template_subgraph_from_mapping(mapping)
        return self.template_graph - sg

    def remaining_template(self, mapping: Mapping) -> Optional[Template]:
        """
        Returns the part of the template that is remaining to be filled out given
        a mapping.
        """
        # if all parameters are fulfilled by the mapping, then return None
        mapping = {k: v for k, v in mapping.items() if v in PARAM}
        mapped_params: Set[URIRef] = {URIRef(v) for v in mapping.values()}
        if not self.template_parameters - mapped_params:
            # return self.building_subgraph_from_mapping(mapping)
            return None
        bindings = {}
        for building_node, param in mapping.items():
            if param is not None:
                bindings[param[len(PARAM) :]] = building_node
        # this *should* be a template because we don't have bindings for all of
        # the template's parameters
        res = self.template.evaluate(bindings)
        assert isinstance(res, Template)
        return res

    def mappings_iter(self, size=None) -> Generator[Mapping, None, None]:
        """
        Returns an iterator over all of the mappings of the given size.
        If size is None, then all mappings are returned in descending order
        of the size of the mapping. This means the most complete mappings
        will be returned first.
        """
        if size is None:
            for size in sorted(self.mappings.keys(), reverse=True):
                for mapping in self.mappings[size]:
                    if not mapping:
                        continue
                    yield mapping
        else:
            for mapping in self.mappings[size]:
                if not mapping:
                    continue
                yield mapping

    def building_mapping_subgraphs_iter(
        self,
        size=None,
    ) -> Generator[Tuple[Mapping, Graph], None, None]:
        """
        Returns an iterator over all of the subgraphs with a mapping of the given
        size. If size is None, then all mappings are returned in descending order
        of the size of the mapping. This means the most complete subgraphs
        will be returned first.
        """
        cache = set()
        for mapping in self.mappings_iter(size):
            subgraph = self.building_subgraph_from_mapping(mapping)
            if not subgraph.connected():
                continue
            key = tuple(sorted(subgraph.all_nodes()))
            if key in cache:
                continue
            cache.add(key)
            yield mapping, subgraph
