from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union
from warnings import warn

from rdflib import BNode, Graph, Literal, URIRef

from buildingmotif.namespaces import OWL, PARAM, RDF, SH, bind_prefixes

if TYPE_CHECKING:
    from buildingmotif.template import Template

Term = Union[URIRef, Literal, BNode]
Triple = Tuple[Term, Term, Term]
_gensym_counter = 0


def _gensym(prefix: str = "p") -> URIRef:
    """
    Generate a unique identifier.
    """
    global _gensym_counter
    _gensym_counter += 1
    return PARAM[f"{prefix}{_gensym_counter}"]


def copy_graph(g: Graph) -> Graph:
    """
    Copy a graph.

    :param g: the graph to copy
    :type g: Graph
    :return: a copy of the input graph
    :rtype: Graph
    """
    c = Graph()
    for t in g.triples((None, None, None)):
        c.add(t)
    return c


def graph_size(g: Graph) -> int:
    """
    Returns the number of triples in a graph

    :param g: graph to be measured
    :type g: Graph
    :return: number of triples in the graph
    :rtype: int
    """
    return len(tuple(g.triples((None, None, None))))


def remove_triples_with_node(g: Graph, node: URIRef) -> None:
    """
    Remove all triples that include the given node. Edits
    the graph in-place

    :param g: the graph to remove triples from
    :type g: Graph
    :param node: the node to remove
    :type node: URIRef
    """
    for s, p, o in g.triples((None, None, None)):
        if s == node or p == node or o == node:
            g.remove((s, p, o))


def replace_nodes(g: Graph, replace: Dict[URIRef, Term]) -> None:
    """
    Replace nodes in a graph.

    :param g: graph to replace nodes in
    :param replace: mapping from old nodes to new nodes
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


def get_template_parts_from_shape(
    shape_name: URIRef, shape_graph: Graph
) -> Tuple[Graph, List[Dict]]:
    """
    Turn a SHACL shape into a template. The following attributes of NodeShapes
    will be incorporated into the resulting template:
    - sh:property with sh:minCount
    - sh:property with sh:qualifiedMinCount
    - sh:class
    - sh:node

    TODO: sh:or?
    """
    # the template body
    body = Graph()
    root_param = PARAM["name"]

    deps = []

    property_shape_query = f"""SELECT ?path ?otype ?mincount WHERE {{
        {shape_name.n3()} sh:property ?prop .
        ?prop sh:path ?path .
        {{ ?prop sh:minCount ?mincount }}
        UNION
        {{ ?prop sh:qualifiedMinCount ?mincount }}

        {{ ?prop sh:qualifiedValueShape?/sh:class ?otype }}
        UNION
        {{ ?prop sh:qualifiedValueShape?/sh:node ?otype }}
    }}"""
    for row in shape_graph.query(property_shape_query):
        # for the type checker; graph.query can return boolean for ASK queries
        assert isinstance(row, tuple)
        (path, otype, mincount) = row
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
    param_types: Dict[URIRef, List[URIRef]]
    prop_types: Dict[URIRef, List[URIRef]]
    prop_values: Dict[URIRef, List[Term]]
    prop_shapes: Dict[URIRef, List[URIRef]]
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
    param_types = defaultdict(list)
    for (param, ptype) in templ_graph.subject_objects(RDF.type):
        param_types[param].append(ptype)

    # store the properties and their types for the target
    prop_types = defaultdict(list)
    prop_values = defaultdict(list)
    prop_shapes = defaultdict(list)
    # TODO: prop_shapes for all properties whose object corresponds to another shape
    for p, o in templ_graph.predicate_objects(target):
        if p == RDF.type:
            continue
        maybe_param = o.removeprefix(PARAM)
        if maybe_param in templ.dependency_parameters:
            prop_shapes[p].append(templ.dependency_for_parameter(maybe_param))
        elif o in param_types:
            prop_types[p].append(param_types[o][0])
        elif o not in PARAM:
            prop_values[p].append(o)
        elif o in PARAM and o not in param_types:
            warn(f"{o} is does not have a type and does not seem to be a literal")
    return _TemplateIndex(
        templ,
        param_types,
        dict(prop_types),
        dict(prop_values),
        dict(prop_shapes),
        target,
    )


def _add_property_shape(
    graph: Graph, name: URIRef, constraint: URIRef, path: URIRef, value: Term
):
    pshape = BNode()
    graph.add((name, SH.property, pshape))
    graph.add((pshape, SH.path, path))
    graph.add((pshape, constraint, value))
    graph.add((pshape, SH["minCount"], Literal(1)))
    graph.add((pshape, SH["maxCount"], Literal(1)))


def _add_qualified_property_shape(
    graph: Graph, name: URIRef, constraint: URIRef, path: URIRef, value: Term
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
    """
    Turn this template into a SHACL shape. If 'use_all' is True, this will
    create a shape that incorporates all templates by the same name in the same library.
    """
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
                    shape, PARAM[templ.name], SH.node, prop, PARAM[shp]
                )

    return shape


def new_temporary_graph(more_namespaces: Optional[dict] = None) -> Graph:
    """
    Creates a new in-memory RDF graph with common and additional namespace bindings.
    """
    g = Graph()
    bind_prefixes(g)
    if more_namespaces:
        for prefix, uri in more_namespaces.items():
            g.bind(prefix, uri)
    return g
