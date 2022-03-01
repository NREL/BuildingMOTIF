from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List
from warnings import warn

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.term import Node

from buildingmotif.namespaces import RDF, SH, bind_prefixes

if TYPE_CHECKING:
    from buildingmotif.template import Template

MARK = Namespace("urn:___mark___#")


@dataclass
class _TemplateIndex:
    template: "Template"
    param_types: Dict[URIRef, List[URIRef]]
    prop_types: Dict[URIRef, List[URIRef]]
    prop_values: Dict[URIRef, List[Node]]
    prop_shapes: Dict[URIRef, List[URIRef]]
    target: URIRef

    @property
    def target_type(self):
        return self.param_types[self.target][0]


def _prep_shape_graph() -> Graph:
    shape = Graph()
    bind_prefixes(shape)
    shape.bind("mark", MARK)
    return shape


def _index_properties(templ: "Template") -> _TemplateIndex:
    templ_graph = templ.evaluate(
        {p: f"mark:{p}" for p in templ.parameters}, {"mark": MARK}
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
        maybe_param = o.removeprefix(MARK)
        if maybe_param in templ.dependency_parameters:
            prop_shapes[p].append(templ.dependency_for_parameter(maybe_param))
        elif o in param_types:
            prop_types[p].append(param_types[o][0])
        elif o not in MARK:
            prop_values[p].append(o)
        elif o in MARK and o not in param_types:
            warn(f"{o} is does not have a type and does not seem to be a literal")
    return _TemplateIndex(
        templ, param_types, prop_types, prop_values, prop_shapes, target
    )


def template_to_shape(template: "Template") -> Graph:
    """
    Turn this template into a SHACL shape. If 'use_all' is True, this will
    create a shape that incorporates all templates by the same name in the same library.

    # TODO: handle use_all
    """
    templ = copy(template)
    shape = _prep_shape_graph()

    idx = _index_properties(templ)

    shape.add((MARK[templ.name], SH.targetClass, idx.target_type))
    # create the shape
    shape.add((MARK[templ.name], RDF.type, SH.NodeShape))
    shape.add((MARK[templ.name], SH["class"], idx.target_type))
    for prop, ptypes in idx.prop_types.items():
        if len(ptypes) == 1:
            _add_property_shape(shape, MARK[templ.name], SH["class"], prop, ptypes[0])
        else:  # more than one ptype
            for ptype in ptypes:
                _add_qualified_property_shape(
                    shape, MARK[templ.name], SH["class"], prop, ptype
                )
    for prop, values in idx.prop_values.items():
        if len(values) == 1:
            _add_property_shape(shape, MARK[templ.name], SH.hasValue, prop, values[0])
        else:  # more than one ptype
            for value in values:
                _add_qualified_property_shape(
                    shape, MARK[templ.name], SH.hasValue, prop, value
                )
    for prop, shapes in idx.prop_shapes.items():
        if len(shapes) == 1:
            _add_property_shape(shape, MARK[templ.name], SH["node"], prop, shapes[0])
        else:  # more than one ptype
            for shp in shapes:
                _add_qualified_property_shape(
                    shape, MARK[templ.name], SH.node, prop, MARK[shp]
                )

            # orn = BNode(f"orn_{target}{prop}")
            # shape.add((pshape, SH["or"], orn))
            # ors = []
            # for ptype in ptypes:
            #     ors.append(BNode())
            #     shape.add((ors[-1], SH["class"], ptype))
            # Collection(shape, orn, ors)

    return shape


def _add_property_shape(
    graph: Graph, name: URIRef, constraint: URIRef, path: URIRef, value: Node
):
    pshape = BNode()
    graph.add((name, SH.property, pshape))
    graph.add((pshape, SH.path, path))
    graph.add((pshape, constraint, value))
    graph.add((pshape, SH["minCount"], Literal(1)))
    graph.add((pshape, SH["maxCount"], Literal(1)))


def _add_qualified_property_shape(
    graph: Graph, name: URIRef, constraint: URIRef, path: URIRef, value: Node
):
    pshape = BNode()
    graph.add((name, SH.property, pshape))
    graph.add((pshape, SH.path, path))
    qvc = BNode()
    graph.add((pshape, SH["qualifiedValueShape"], qvc))
    graph.add((qvc, constraint, value))
    graph.add((pshape, SH["qualifiedMinCount"], Literal(1)))
    graph.add((pshape, SH["qualifiedMaxCount"], Literal(1)))
