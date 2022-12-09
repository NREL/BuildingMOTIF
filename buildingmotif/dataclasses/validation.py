from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from itertools import chain
from secrets import token_hex
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

import rdflib
from rdflib import Graph, URIRef

from buildingmotif import get_building_motif
from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.namespaces import CONSTRAINT, PARAM, SH, A
from buildingmotif.utils import _gensym, get_template_parts_from_shape, replace_nodes

if TYPE_CHECKING:
    from buildingmotif.dataclasses import Library, Model, Template


@dataclass(frozen=True)
class GraphDiff:
    """
    An abstraction of a SHACL Validation Result that can produce a Template
    which resolves the difference between the expected and actual graph.

    Each GraphDiff has a 'focus' which is the node in the model that the
    GraphDiff is about. If 'focus' is None, then the GraphDiff is about the
    model itself rather than a specific node
    """

    focus: Optional[URIRef]
    graph: Graph

    def resolve(self, lib: "Library") -> List["Template"]:
        """
        Produces a list of templates to resolve this GraphDiff

        :param lib: The library to hold the templates
        :type lib: "Library"
        :return: Templates that reconcile the GraphDiff
        :rtype: List["Template"]
        """
        raise NotImplementedError

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff"""
        raise NotImplementedError

    def __hash__(self):
        return hash(self.reason())


@dataclass(frozen=True)
class PathClassCount(GraphDiff):
    """
    Represents an entity missing paths to objects of a given type:

        $this <path> <object> .
        <object> a <classname> .
    """

    path: URIRef
    minc: Optional[int]
    maxc: Optional[int]
    classname: URIRef

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff"""

        if self.minc == self.maxc:
            return f"{self.focus} needs exactly {self.minc} instances of \
{self.classname} on path {self.path}"
        elif (self.minc is None or self.minc == 0) and self.maxc is not None:
            return f"{self.focus} needs at most {self.maxc} instances of \
{self.classname} on path {self.path}"
        elif self.maxc is None and self.minc is not None:
            return f"{self.focus} needs at least {self.minc} instances of \
{self.classname} on path {self.path}"
        else:
            return f"{self.focus} needs between {self.minc} and {self.maxc} instances of \
{self.classname} on path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """
        Produces a list of templates to resolve this GraphDiff

        :param lib: The library to hold the templates
        :type lib: "Library"
        :return: Templates that reconcile the GraphDiff
        :rtype: List["Template"]
        """
        assert self.focus is not None
        body = Graph()
        for i in range(self.minc or 0):
            inst = _gensym()
            body.add((self.focus, self.path, inst))
            body.add((inst, A, self.classname))
        return [lib.create_template(f"resolve_{token_hex(4)}", body)]


@dataclass(frozen=True, unsafe_hash=True)
class PathShapeCount(GraphDiff):
    """
    Represents an entity missing paths to objects that match a given shape

        $this <path> <object> .
        <object> a <shapename> .
    """

    path: URIRef = field(hash=True)
    minc: Optional[int] = field(hash=True)
    maxc: Optional[int] = field(hash=True)
    shapename: URIRef = field(hash=True)
    extra_body: Optional[Graph] = field(hash=False)
    extra_deps: Optional[Tuple] = field(hash=False)

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff"""
        if self.minc == self.maxc:
            return f"{self.focus} needs exactly {self.minc} instances of \
{self.shapename} on path {self.path}"
        elif (self.minc is None or self.minc == 0) and self.maxc is not None:
            return f"{self.focus} needs at most {self.maxc} instances of \
{self.shapename} on path {self.path}"
        elif self.maxc is None and self.minc is not None:
            return f"{self.focus} needs at least {self.minc} instances of \
{self.shapename} on path {self.path}"
        else:
            return f"{self.focus} needs between {self.minc} and {self.maxc} instances of \
{self.shapename} on path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """Produces a list of templates to resolve this GraphDiff"""
        assert self.focus is not None
        generated = []
        if self.extra_deps:
            for dep in self.extra_deps:
                dep["args"] = {k: str(v)[len(PARAM) :] for k, v in dep["args"].items()}
        for _ in range(self.minc or 0):
            body = Graph()
            inst = PARAM["name"]
            body.add((self.focus, self.path, inst))
            body.add((inst, A, self.shapename))
            if self.extra_body:
                replace_nodes(self.extra_body, {PARAM.name: inst})
                body += self.extra_body
            templ = lib.create_template(f"resolve{token_hex(4)}", body)
            if self.extra_deps:
                from buildingmotif.dataclasses.template import Template

                bm = get_building_motif()
                for dep in self.extra_deps:
                    dbt = bm.table_connection.get_db_template_by_name(dep["template"])
                    t = Template.load(dbt.id)
                    templ.add_dependency(t, dep["args"])
            generated.append(templ)
        return generated


@dataclass(frozen=True)
class RequiredPath(GraphDiff):
    """
    Represents an entity missing a required property
    """

    path: URIRef
    minc: Optional[int]
    maxc: Optional[int]

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff"""
        if self.minc == self.maxc:
            return f"{self.focus} needs exactly {self.minc} uses of \
path {self.path}"
        elif (self.minc is None or self.minc == 0) and self.maxc is not None:
            return f"{self.focus} needs at most {self.maxc} uses of \
path {self.path}"
        elif self.maxc is None and self.minc is not None:
            return f"{self.focus} needs at least {self.minc} uses of \
path {self.path}"
        else:
            return f"{self.focus} needs between {self.minc} and {self.maxc} uses of \
path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """
        Produces a list of templates to resolve this GraphDiff

        :param lib: The library to hold the templates
        :type lib: "Library"
        :return: Templates that reconcile the GraphDiff
        :rtype: List["Template"]
        """
        assert self.focus is not None
        body = Graph()
        for _ in range(self.minc or 0):
            inst = _gensym()
            body.add((self.focus, self.path, inst))
        return [lib.create_template(f"resolve{token_hex(4)}", body)]


@dataclass(frozen=True)
class RequiredClass(GraphDiff):
    """
    Represents an entity that should be an instance of the indicated class
    """

    classname: URIRef

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff"""
        return f"{self.focus} needs to be a {self.classname}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """
        Produces a list of templates to resolve this GraphDiff

        :param lib: The library to hold the templates
        :type lib: "Library"
        :return: Templates that reconcile the GraphDiff
        :rtype: List["Template"]
        """
        assert self.focus is not None
        body = Graph()
        body.add((self.focus, A, self.classname))
        return [lib.create_template(f"resolve{token_hex(4)}", body)]


@dataclass(frozen=True)
class GraphClassCardinality(GraphDiff):
    """
    Represents a graph that is missing an expected number of instances
    of the given class
    """

    classname: URIRef
    expectedCount: int

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff"""
        return f"Graph did not have {self.expectedCount} instances of {self.classname}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """
        Produces a list of templates to resolve this GraphDiff

        :param lib: The library to hold the templates
        :type lib: "Library"
        :return: Templates that reconcile the GraphDiff
        :rtype: List["Template"]
        """
        templs = []
        for _ in range(self.expectedCount):
            template_body = Graph()
            template_body.add((PARAM["name"], A, self.classname))
            templs.append(lib.create_template(f"resolve{token_hex(4)}", template_body))
        return templs


@dataclass
class ValidationContext:
    """
    Holds the necessary information for processing the results of SHACL validation.
    """

    shape_collections: List[ShapeCollection]
    valid: bool
    report: rdflib.Graph
    report_string: str
    model: "Model"

    @cached_property
    def diffset(self) -> Set[GraphDiff]:
        """
        The unordered set of GraphDiffs produced from interpreting the
        input SHACL validation report
        """
        return self._report_to_diffset()

    @cached_property
    def _context(self) -> Graph:
        return sum((sc.graph for sc in self.shape_collections), start=Graph())  # type: ignore

    def as_templates(self) -> List["Template"]:
        """
        Produces the set of templates that reconcile the GraphDiffs from
        the SHACL validation report

        :return: Reconciling templates
        :rtype: List["Template"]
        """
        return diffset_to_templates(self.diffset)

    def _report_to_diffset(self) -> Set[GraphDiff]:
        """
        Interpret a SHACL validation report and say what is missing.

        :return: A set of 'GraphDiff's that each abstract a SHACL shape violation
        :rtype: Set[GraphDiff]
        """
        classpath = SH["class"] | (SH.qualifiedValueShape / SH["class"])  # type: ignore
        shapepath = SH["node"] | (SH.qualifiedValueShape / SH["node"])  # type: ignore
        # TODO: for future use
        # proppath = SH["property"] | (SH.qualifiedValueShape / SH["property"])  # type: ignore

        g = self.report + self._context
        diffs: Set[GraphDiff] = set()
        for result in g.objects(predicate=SH.result):
            # check if the failure is due to our count constraint component
            focus = g.value(result, SH.focusNode)
            if (
                g.value(result, SH.sourceConstraintComponent)
                == CONSTRAINT.countConstraintComponent
            ):
                expected_count = g.value(
                    result, SH.sourceShape / CONSTRAINT.exactCount  # type: ignore
                )
                of_class = g.value(result, SH.sourceShape / CONSTRAINT["class"])  # type: ignore
                # here, our 'self.focus' is the graph itself, which we don't want to have bound
                # to the templates during evaluation (for this specific kind of diff).
                # For this reason we override focus to be None
                diffs.add(GraphClassCardinality(None, g, of_class, int(expected_count)))
            elif (
                g.value(result, SH.sourceConstraintComponent)
                == SH.ClassConstraintComponent
            ):
                requiring_shape = g.value(result, SH.sourceShape)
                expected_class = g.value(requiring_shape, SH["class"])
                diffs.add(RequiredClass(focus, g, expected_class))
            elif (
                g.value(result, SH.sourceConstraintComponent)
                == SH.NodeConstraintComponent
            ):
                # TODO: handle node constraint components
                pass
            # check if property shape
            elif g.value(result, SH.resultPath):
                path = g.value(result, SH.resultPath)
                min_count = g.value(
                    result, SH.sourceShape / (SH.minCount | SH.qualifiedMinCount)  # type: ignore
                )
                max_count = g.value(
                    result, SH.sourceShape / (SH.maxCount | SH.qualifiedMaxCount)  # type: ignore
                )
                classname = g.value(
                    result,
                    SH.sourceShape / classpath,
                )

                # TODO: finish this for some shapes
                # shapes_of_object = g.value(result, SH.sourceShape / SH.qualifiedValueShape)
                # for soo in shapes_of_object:
                #     soo_graph = g.cbd(soo)
                # handle properties (on qualifiedValueShapes?)
                # extra = g.value(result, SH.sourceShape / proppath)  # type: ignore

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
                    continue
                shapename = g.value(result, SH.sourceShape / shapepath)  # type: ignore
                if focus and (min_count or max_count) and shapename:
                    extra_body, deps = get_template_parts_from_shape(shapename, g)
                    diffs.add(
                        PathShapeCount(
                            focus,
                            g,
                            path,
                            int(min_count) if min_count else None,
                            int(max_count) if max_count else None,
                            shapename,
                            extra_body,
                            tuple(deps),
                        )
                    )
                    continue
                if focus and (min_count or max_count):
                    diffs.add(
                        RequiredPath(
                            focus,
                            g,
                            path,
                            int(min_count) if min_count else None,
                            int(max_count) if max_count else None,
                        )
                    )
        return diffs


def diffset_to_templates(diffset: Set[GraphDiff]) -> List["Template"]:
    """
    Combine GraphDiff by focus node to generate a list of templates that
    reconcile what is "wrong" with the graph with respect to the graph diffs

    :param diffset: A set of diffs produced by report_to_diffset
    :type diffset: Set[GraphDiff]
    :return: List of templates that when populated should resolve the SHACL violations
    :rtype: List[Template]
    """
    from buildingmotif.dataclasses import Library, Template

    related: Dict[URIRef, Set[GraphDiff]] = defaultdict(set)
    unfocused: List[Template] = []
    lib = Library.create(f"resolve_{token_hex(4)}")
    # compute the GROUP BY GraphDiff.focus
    for diff in diffset:
        if diff.focus is None:
            unfocused.extend(diff.resolve(lib))
        else:
            related[diff.focus].add(diff)

    templates = []
    # add all templates that don't have a focus node
    templates.extend(unfocused)
    # now merge all tempaltes together for each focus node
    for focus, diffset in related.items():
        templ_lists = (diff.resolve(lib) for diff in diffset)
        templs = list(filter(None, chain.from_iterable(templ_lists)))
        if len(templs) <= 1:
            templates.extend(templs)
            continue
        base = templs[0]
        # treat all the other templates as dependencies of the first one.
        # This allows us to do a "join" with inline_dependencies() which
        # will ensure that there are no unintended overlaps in the choice
        # of parameter name
        for templ in templs[1:]:
            # if there is a 'name' in the parameter list, join on that name.
            # otherwise, just append the body
            # (we don't need to use use to_inline() to ensure uniqueness of parameters
            # because all params are created with _gensym() which ensures uniqueness)
            if "name" in templ.parameters:
                base.add_dependency(templ, {"name": "name"})
            else:
                base.body += templ.body
        unified = base.inline_dependencies()
        # only try to evaluate if there are parameters, else this will fail.
        # We may not have parameters if the GraphDiffs have all the information
        # they need to patch the graph and don't need user input
        if len(unified.parameters) > 0:
            unified_evaluated = unified.evaluate({"name": focus})
        else:
            unified_evaluated = unified
        assert isinstance(unified_evaluated, Template)
        templates.append(unified_evaluated)
    return templates
