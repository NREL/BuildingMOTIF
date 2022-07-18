import logging
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from secrets import token_hex
from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, Set, Tuple, Union

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.paths import ZeroOrOne

from buildingmotif.namespaces import CONSTRAINT, OWL, PARAM, RDF, SH, A, bind_prefixes

if TYPE_CHECKING:
    from buildingmotif.dataclasses import Library, Template

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


def combine_graphs(*graphs: Graph) -> Graph:
    """
    Combine all of the graphs into a new graph
    """
    newg = Graph()
    for graph in graphs:
        newg += graph
    return newg


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
    for triple in g.triples((node, None, None)):
        g.remove(triple)
    for triple in g.triples((None, node, None)):
        g.remove(triple)
    for triple in g.triples((None, None, node)):
        g.remove(triple)


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


def get_ontology_files(directory: Path, recursive: bool = True) -> List[Path]:
    """
    Returns a list of all ontology files in the given directory. If recursive
    is true, traverses the directory structure to find ontology files not just
    in the given directory

    :param directory: the directory to begin the search
    :type directory: Path
    :param recursive: if true, find ontology files in nested directories, defaults to True
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

    pshapes = shape_graph.objects(subject=shape_name, predicate=SH["property"])
    for pshape in pshapes:
        property_path = shape_graph.value(pshape, SH["path"])
        # TODO: expand otypes to include sh:in, sh:or, or no datatype at all!
        otypes = list(
            shape_graph.objects(
                subject=pshape,
                predicate=SH["qualifiedValueShape"]
                * ZeroOrOne
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
            logging.warn(
                f"{o} is does not have a type and does not seem to be a literal"
            )
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


"""
For each of these, need a consistent API:
- generate a template that resolves the diff
- then we can use the monomorphism search to remove redundant effort:
    - how much of this diff is already solved?
"""


@dataclass(frozen=True)
class GraphDiff:
    focus: URIRef
    graph: Graph
    counter: ClassVar[int] = 0

    def resolve(self, lib: "Library") -> "Template":
        raise NotImplementedError

    def reason(self) -> str:
        raise NotImplementedError

    def __hash__(self):
        return hash(self.reason())


@dataclass(frozen=True)
class PathClassCount(GraphDiff):
    path: URIRef
    minc: Optional[int]
    maxc: Optional[int]
    classname: URIRef

    def reason(self) -> str:
        return f"Needed between {self.minc} and {self.maxc} instances of {self.classname} \
on path {self.path}"

    def resolve(self, lib: "Library") -> "Template":
        body = Graph()
        for i in range(self.minc or 0):
            inst = _gensym()
            body.add((PARAM["name"], self.path, inst))
            body.add((inst, A, self.classname))
        return lib.create_template(f"resolve_{token_hex(4)}", body)


@dataclass(frozen=True)
class PathShapeCount(GraphDiff):
    path: URIRef
    minc: Optional[int]
    maxc: Optional[int]
    shapename: URIRef

    def reason(self) -> str:
        return f"Needed between {self.minc} and {self.maxc} instances of {self.shapename} \
on path {self.path}"

    def resolve(self, lib: "Library") -> "Template":
        body = Graph()
        for _ in range(self.minc or 0):
            inst = _gensym()
            body.add((PARAM["name"], self.path, inst))
            body.add((inst, A, self.shapename))
        return lib.create_template(f"resolve{token_hex(4)}", body)


@dataclass(frozen=True)
class GraphClassCardinality(GraphDiff):
    classname: URIRef
    expectedCount: int

    def reason(self) -> str:
        return f"Graph did not have {self.expectedCount} instances of {self.classname}"

    def resolve(self, lib: "Library") -> "Template":
        template_body = Graph()
        for i in range(self.expectedCount):
            template_body.add((PARAM[f"inst_{i}"], A, self.classname))

        return lib.create_template(f"resolve{token_hex(4)}", template_body)


def process_shacl_validation_report(report: Graph, aux: Graph) -> List["Template"]:
    """
    Interpret a SHACL validation report and say what is missing.

    Standard 'report' or 'diff' object:
    - focus node (could be the graph itself e.g. for cardinality constraints or an instance)
    - (path, class, mincount, maxcount)
    - (path, shape, mincount, maxcount)
    """

    g = report + aux
    diffs: Set[GraphDiff] = set()
    for result in g.objects(predicate=SH.result):
        print("result")
        # check if the failure is due to our count constraint component
        focus = g.value(result, SH.focusNode)
        if (
            g.value(result, SH.sourceConstraintComponent)
            == CONSTRAINT.countConstraintComponent
        ):
            expected_count = g.value(result, SH.sourceShape / CONSTRAINT.exactCount)
            of_class = g.value(result, SH.sourceShape / CONSTRAINT["class"])
            diffs.add(GraphClassCardinality(focus, g, of_class, int(expected_count)))
        # check if property shape
        elif g.value(result, SH.resultPath):
            path = g.value(result, SH.resultPath)
            min_count = g.value(
                result, SH.sourceShape / (SH.minCount | SH.qualifiedMinCount)
            )
            max_count = g.value(
                result, SH.sourceShape / (SH.maxCount | SH.qualifiedMaxCount)
            )
            classname = g.value(
                result,
                SH.sourceShape / (SH["class"] | (SH.qualifiedValueShape / SH["class"])),
            )
            if focus and (min_count or max_count) and classname:
                diffs.add(
                    PathClassCount(
                        focus,
                        g,
                        path,
                        int(min_count) if min_count else None,
                        int(max_count) if max_count else None,
                        classname,
                    )
                )
            shapename = g.value(
                result, SH.sourceShape / (SH.node | (SH.qualifiedValueShape / SH.node))
            )
            if focus and (min_count or max_count) and shapename:
                diffs.add(
                    PathShapeCount(
                        focus,
                        g,
                        path,
                        int(min_count) if min_count else None,
                        int(max_count) if max_count else None,
                        shapename,
                    )
                )
    # for diff in diffs:
    #    print("---")
    #    print(diff.focus)
    #    print(diff.reason())

    templs = diffset_to_templates(diffs)
    # for t in templs:
    #    print('*'*80)
    #    print(t.name)
    #    print(t.body.serialize())
    return templs
    #    templ = diff.resolve(lib)
    #    if templ:
    #        print(templ.body.serialize())


def diffset_to_templates(diffset: Set[GraphDiff]) -> List["Template"]:
    """
    Combine GraphDiff by focus node to generate
    """
    from buildingmotif.dataclasses import Library

    related: Dict[URIRef, Set[GraphDiff]] = defaultdict(set)
    lib = Library.create("resolve")
    # compute the GROUP BY GraphDiff.focus
    for diff in diffset:
        related[diff.focus].add(diff)

    from pprint import pprint

    pprint(related)

    templates = []
    for focus, diffset in related.items():
        templs = [t for t in (diff.resolve(lib) for diff in diffset) if t]
        if len(templs) <= 1:
            templates.extend(templs)
            continue
        base = templs[0]
        for templ in templs[1:]:
            base.add_dependency(templ, {"name": "name"})
        unified = base.inline_dependencies()
        unified = unified.evaluate({"name": focus})
        templates.append(unified)
    return templates
