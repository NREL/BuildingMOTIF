import logging
import secrets
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.paths import ZeroOrOne
from rdflib.term import Node

from buildingmotif.namespaces import OWL, PARAM, RDF, SH, bind_prefixes

if TYPE_CHECKING:
    from buildingmotif.dataclasses import Template

Triple = Tuple[Node, Node, Node]
_gensym_counter = 0


def _gensym(prefix: str = "p") -> URIRef:
    """
    Generate a unique identifier.
    """
    global _gensym_counter
    _gensym_counter += 1
    return PARAM[f"{prefix}{_gensym_counter}"]


def copy_graph(g: Graph, preserve_blank_nodes: bool = True) -> Graph:
    """
    Copy a graph. Creates new blank nodes so that these remain unique to each Graph

    :param g: the graph to copy
    :type g: Graph
    :param preserve_blank_nodes: if true, keep blank nodes the same when copying the graph
    :type preserve_blank_nodes: boolean, defaults to True
    :return: a copy of the input graph
    :rtype: Graph
    """
    c = Graph()
    for pfx, ns in g.namespaces():
        c.bind(pfx, ns)
    new_prefix = secrets.token_hex(4)
    for t in g.triples((None, None, None)):
        assert isinstance(t, tuple)
        (s, p, o) = t
        if not preserve_blank_nodes:
            if isinstance(s, BNode):
                s = BNode(value=new_prefix + s.toPython())
            if isinstance(p, BNode):
                p = BNode(value=new_prefix + p.toPython())
            if isinstance(o, BNode):
                o = BNode(value=new_prefix + o.toPython())
        c.add((s, p, o))
    return c


def inline_sh_nodes(g: Graph):
    """
    Recursively inlines all sh:node properties and objects on the graph.

    :param g: graph to be edited
    :type g: Graph
    """
    q = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    CONSTRUCT {
        ?parent ?p ?o .
    }
    WHERE {
        ?parent sh:node ?child .
        ?child ?p ?o
    }"""
    original_size = 0
    while original_size != len(g):  # type: ignore
        original_size = len(g)  # type: ignore
        for (s, p, o) in g.query(q):  # type: ignore
            if p == RDF.type and o == SH.NodeShape:
                continue
            g.add((s, p, o))
        break


def combine_graphs(*graphs: Graph) -> Graph:
    """Combine all of the graphs into a new graph.

    :return: combined graph
    :rtype: Graph
    """
    newg = Graph()
    for graph in graphs:
        newg += graph
    return newg


def graph_size(g: Graph) -> int:
    """Returns the number of triples in a graph.

    :param g: graph to be measured
    :type g: Graph
    :return: number of triples in the graph
    :rtype: int
    """
    return len(tuple(g.triples((None, None, None))))


def remove_triples_with_node(g: Graph, node: URIRef) -> None:
    """Remove all triples that include the given node. Edits the graph
    in-place.

    :param g: the graph to remove triples from
    :type g: Graph
    :param node: the node to remove
    :type node: URIRef
    """
    for triple in g.triples((node, None, None)):
        g.remove(triple)
    for triple in g.triples((None, node, None)):
        g.remove(triple)
    for triple in g.triples((None, None, node)):
        g.remove(triple)


def replace_nodes(g: Graph, replace: Dict[Node, Node]) -> None:
    """Replace nodes in a graph.

    :param g: graph to replace nodes in
    :type g: Graph
    :param replace: dict mapping old nodes to new nodes
    :type replace: Dict[Node, Node]
    """
    for s, p, o in g.triples((None, None, None)):
        g.remove((s, p, o))
        if s in replace:
            s = replace[s]
        if p in replace:
            p = replace[p]
        if o in replace:
            o = replace[o]
        g.add((s, p, o))


def get_ontology_files(directory: Path, recursive: bool = True) -> List[Path]:
    """Returns a list of all ontology files in the given directory.

    If recursive is true, traverses the directory structure to find ontology
    files not just in the given directory.

    :param directory: the directory to begin the search
    :type directory: Path
    :param recursive: if true, find ontology files in nested directories,
        defaults to true
    :type recursive: bool, optional
    :return: a list of filenames
    :rtype: List[Path]
    """
    patterns = [
        "*.ttl",
        "*.n3",
        "*.rdf",
        "*.xml",
    ]
    if recursive:
        searches = (directory.rglob(f"{pat}") for pat in patterns)
    else:
        searches = (directory.glob(f"{pat}") for pat in patterns)
    return list(chain.from_iterable(searches))


def get_template_parts_from_shape(
    shape_name: URIRef, shape_graph: Graph
) -> Tuple[Graph, List[Dict]]:
    """Turn a SHACL shape into a template. The following attributes of
    NodeShapes will be incorporated into the resulting template:
    - sh:property with sh:minCount
    - sh:property with sh:qualifiedMinCount
    - sh:class
    - sh:node

    :param shape_name: name of shape
    :type shape_name: URIRef
    :param shape_graph: shape graph
    :type shape_graph: Graph
    :raises Exception: if more than one object type detected on shape
    :raises Exception: if more than one min count detected on shape
    :return: template parts
    :rtype: Tuple[Graph, List[Dict]]
    """
    # TODO: sh:or?
    # the template body
    body = Graph()
    root_param = PARAM["name"]

    deps = []

    pshapes = shape_graph.objects(subject=shape_name, predicate=SH["property"])
    for pshape in pshapes:
        property_path = shape_graph.value(pshape, SH["path"])
        # TODO: expand otypes to include sh:in, sh:or, or no datatype at all!
        otypes = list(
            shape_graph.objects(
                subject=pshape,
                predicate=SH["qualifiedValueShape"]
                * ZeroOrOne  # type:ignore
                / (SH["class"] | SH["node"] | SH["datatype"]),
            )
        )
        mincounts = list(
            shape_graph.objects(
                subject=pshape, predicate=SH["minCount"] | SH["qualifiedMinCount"]
            )
        )
        if len(otypes) > 1:
            raise Exception(f"more than one object type detected on {shape_name}")
        if len(mincounts) > 1:
            raise Exception(f"more than one min count detected on {shape_name}")
        if len(mincounts) == 0 or len(otypes) == 0:
            # print(f"No useful information on {shape_name} - {pshape}")
            # print(shape_graph.cbd(pshape).serialize())
            continue
        (path, otype, mincount) = property_path, otypes[0], mincounts[0]
        assert isinstance(mincount, Literal)

        for _ in range(int(mincount)):
            param = _gensym()
            body.add((root_param, path, param))
            deps.append({"template": otype, "args": {"name": param}})
            # body.add((param, RDF.type, otype))

    if (shape_name, RDF.type, OWL.Class) in shape_graph:
        body.add((root_param, RDF.type, shape_name))

    classes = shape_graph.objects(shape_name, SH["class"])
    for cls in classes:
        body.add((root_param, RDF.type, cls))

    nodes = shape_graph.objects(shape_name, SH["node"])
    for node in nodes:
        deps.append({"template": node, "args": {"name": "name"}})  # tie to root param

    return body, deps


@dataclass
class _TemplateIndex:
    template: "Template"
    param_types: Dict[Node, List[Node]]
    prop_types: Dict[Node, List[Node]]
    prop_values: Dict[Node, List[Node]]
    prop_shapes: Dict[Node, List[Node]]
    target: URIRef

    @property
    def target_type(self):
        return self.param_types[self.target][0]


def _prep_shape_graph() -> Graph:
    shape = Graph()
    bind_prefixes(shape)
    shape.bind("mark", PARAM)
    return shape


def _index_properties(templ: "Template") -> _TemplateIndex:
    templ_graph = templ.evaluate(
        {p: PARAM[p] for p in templ.parameters}, {"mark": PARAM}
    )
    assert isinstance(templ_graph, Graph)

    # pick a random node to act as the 'target' of the shape
    target = next(iter(templ_graph.subjects(RDF.type)))
    print(f"Choosing {target} as the target of the shape")
    assert isinstance(target, URIRef)

    # store the classes for each parameter
    param_types: Dict[Node, List[Node]] = defaultdict(list)
    for (param, ptype) in templ_graph.subject_objects(RDF.type):
        param_types[param].append(ptype)

    # store the properties and their types for the target
    prop_types: Dict[Node, List[Node]] = defaultdict(list)
    prop_values: Dict[Node, List[Node]] = defaultdict(list)
    prop_shapes: Dict[Node, List[Node]] = defaultdict(list)
    # TODO: prop_shapes for all properties whose object corresponds to another shape
    for p, o in templ_graph.predicate_objects(target):
        if p == RDF.type:
            continue
        # maybe_param = str(o).removeprefix(PARAM) Python >=3.9
        maybe_param = str(o)[len(PARAM) :]
        if maybe_param in templ.dependency_parameters:
            dep = templ.dependency_for_parameter(maybe_param)
            if dep is not None:
                prop_shapes[p].append(URIRef(dep._name))
        elif o in param_types:
            prop_types[p].append(param_types[o][0])
        elif str(o) not in PARAM:
            prop_values[p].append(o)
        elif str(o) in PARAM and o not in param_types:
            logging.warn(
                f"{o} is does not have a type and does not seem to be a literal"
            )
    return _TemplateIndex(
        templ,
        dict(param_types),
        dict(prop_types),
        dict(prop_values),
        dict(prop_shapes),
        target,
    )


def _add_property_shape(
    graph: Graph, name: Node, constraint: Node, path: Node, value: Node
):
    pshape = BNode()
    graph.add((name, SH.property, pshape))
    graph.add((pshape, SH.path, path))
    graph.add((pshape, constraint, value))
    graph.add((pshape, SH["minCount"], Literal(1)))
    graph.add((pshape, SH["maxCount"], Literal(1)))


def _add_qualified_property_shape(
    graph: Graph, name: Node, constraint: Node, path: Node, value: Node
):
    pshape = BNode()
    graph.add((name, SH.property, pshape))
    graph.add((pshape, SH.path, path))
    qvc = BNode()
    graph.add((pshape, SH["qualifiedValueShape"], qvc))
    graph.add((qvc, constraint, value))
    graph.add((pshape, SH["qualifiedMinCount"], Literal(1)))
    graph.add((pshape, SH["qualifiedMaxCount"], Literal(1)))


def template_to_shape(template: "Template") -> Graph:
    """Turn this template into a SHACL shape.

    :param template: template to convert
    :type template: template
    :return: graph of template
    :rtype: Graph
    """
    # TODO If 'use_all' is True, this will create a shape that incorporates all
    # Templates by the same name in the same Library.
    templ = copy(template)
    shape = _prep_shape_graph()

    idx = _index_properties(templ)

    shape.add((PARAM[templ.name], SH.targetClass, idx.target_type))
    # create the shape
    shape.add((PARAM[templ.name], RDF.type, SH.NodeShape))
    shape.add((PARAM[templ.name], SH["class"], idx.target_type))
    for prop, ptypes in idx.prop_types.items():
        if len(ptypes) == 1:
            _add_property_shape(shape, PARAM[templ.name], SH["class"], prop, ptypes[0])
        else:  # more than one ptype
            for ptype in ptypes:
                _add_qualified_property_shape(
                    shape, PARAM[templ.name], SH["class"], prop, ptype
                )
    for prop, values in idx.prop_values.items():
        if len(values) == 1:
            _add_property_shape(shape, PARAM[templ.name], SH.hasValue, prop, values[0])
        else:  # more than one ptype
            for value in values:
                _add_qualified_property_shape(
                    shape, PARAM[templ.name], SH.hasValue, prop, value
                )
    for prop, shapes in idx.prop_shapes.items():
        if len(shapes) == 1:
            _add_property_shape(shape, PARAM[templ.name], SH["node"], prop, shapes[0])
        else:  # more than one ptype
            for shp in shapes:
                _add_qualified_property_shape(
                    # TODO: fix this?
                    shape,
                    PARAM[templ.name],
                    SH.node,
                    prop,
                    PARAM[str(shp)],
                )

    return shape


def new_temporary_graph(more_namespaces: Optional[dict] = None) -> Graph:
    """Creates a new in-memory RDF graph with common and additional namespace
    bindings.

    :param more_namespaces: namespaces, defaults to None
    :type more_namespaces: Optional[dict], optional
    :return: graph with namespaces
    :rtype: Graph
    """
    g = Graph()
    bind_prefixes(g)
    if more_namespaces:
        for prefix, uri in more_namespaces.items():
            g.bind(prefix, uri)
    return g


def get_parameters(graph: Graph) -> Set[str]:
    """Returns the set of parameter names in the given graph.

    Parameters are identified by the PARAM namespace, `urn:___param___#`. This
    method returns the names of the parameters, not the full URIs. For example,
    the parameter `urn:___param___#abc` in a graph would be returned as `abc`.

    :param graph: a graph containing parameters
    :type graph: Graph
    :return: a set of the parameter names in the graph
    :rtype: Set[str]
    """
    # get an iterable of all nodes in the graph
    all_nodes = chain.from_iterable(graph.triples((None, None, None)))
    # get all nodes in the PARAM namespace
    params = {str(node) for node in all_nodes if str(node).startswith(PARAM)}
    # extract the 'value' part of the param, which is the name of the parameter
    return {node[len(PARAM) :] for node in params}


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
    This detects the use of 'sh:and' on SHACL NodeShapes and inlines
    all of the included shapes
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
