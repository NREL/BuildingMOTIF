from rdflib import Graph

from buildingmotif.namespaces import SH
from buildingmotif.utils import copy_graph


def _inline_sh_node(sg: Graph):
    """
    This detects the use of 'sh:node' on SHACL NodeShapes and inlines
    the shape they point to.
    """
    q = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    SELECT ?parent ?child WHERE {
        ?parent a sh:NodeShape ;
                sh:node ?child .
        }"""
    for row in sg.query(q):
        parent, child = row
        sg.remove((parent, SH.node, child))
        pos = sg.predicate_objects(child)
        for (p, o) in pos:
            sg.add((parent, p, o))


def _inline_sh_and(sg: Graph):
    """
    This detects the use of 'sh:node' on SHACL NodeShapes and inlines
    the shape they point to.
    """
    q = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    SELECT ?parent ?child ?andnode WHERE {
        ?parent a sh:NodeShape ;
                sh:and ?andnode .
        ?andnode rdf:rest*/rdf:first ?child .
        }"""
    for row in sg.query(q):
        parent, child, to_remove = row
        sg.remove((parent, SH["and"], to_remove))
        pos = sg.predicate_objects(child)
        for (p, o) in pos:
            sg.add((parent, p, o))


def _iterate_branches(sg: Graph):
    pass


def rewrite_shape_graph(g: Graph) -> Graph:
    """
    Rewrites the input graph to make the resulting validation report more useful.

    :param g: the shape graph to rewrite
    :type g: Graph
    :return: a *copy* of the original shape graph w/ rewritten shapes
    :rtype: Graph
    """
    sg = copy_graph(g)

    previous_size = -1
    while len(sg) != previous_size:  # type: ignore
        previous_size = len(sg)  # type: ignore
        _inline_sh_and(sg)
        # make sure to handle sh:node *after* sh:and
        _inline_sh_node(sg)
    return sg
