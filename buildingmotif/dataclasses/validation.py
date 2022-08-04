from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from itertools import chain
from secrets import token_hex
from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, Set

import rdflib
from rdflib import Graph, URIRef

from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.namespaces import CONSTRAINT, PARAM, SH, A
from buildingmotif.utils import _gensym

if TYPE_CHECKING:
    from buildingmotif.dataclasses import Library, Model, Template


@dataclass(frozen=True)
class GraphDiff:
    focus: Optional[URIRef]
    graph: Graph
    counter: ClassVar[int] = 0

    def resolve(self, lib: "Library") -> List["Template"]:
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
        return f"{self.focus} needs between {self.minc} and {self.maxc} instances of \
{self.classname} on path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        assert self.focus is not None
        body = Graph()
        for i in range(self.minc or 0):
            inst = _gensym()
            body.add((self.focus, self.path, inst))
            body.add((inst, A, self.classname))
        return [lib.create_template(f"resolve_{token_hex(4)}", body)]


@dataclass(frozen=True)
class PathShapeCount(GraphDiff):
    path: URIRef
    minc: Optional[int]
    maxc: Optional[int]
    shapename: URIRef

    def reason(self) -> str:
        return f"{self.focus} needs between {self.minc} and {self.maxc} instances of \
{self.shapename} on path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        assert self.focus is not None
        body = Graph()
        for _ in range(self.minc or 0):
            inst = _gensym()
            body.add((self.focus, self.path, inst))
            body.add((inst, A, self.shapename))
        return [lib.create_template(f"resolve{token_hex(4)}", body)]


@dataclass(frozen=True)
class RequiredPath(GraphDiff):
    path: URIRef
    minc: Optional[int]
    maxc: Optional[int]

    def reason(self) -> str:
        return f"{self.focus} needs between {self.minc} and {self.maxc} uses \
of path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        assert self.focus is not None
        body = Graph()
        for _ in range(self.minc or 0):
            inst = _gensym()
            body.add((self.focus, self.path, inst))
        return [lib.create_template(f"resolve{token_hex(4)}", body)]


@dataclass(frozen=True)
class RequiredClass(GraphDiff):
    classname: URIRef

    def reason(self) -> str:
        return f"{self.focus} needs to be a {self.classname}"

    def resolve(self, lib: "Library") -> List["Template"]:
        assert self.focus is not None
        body = Graph()
        body.add((self.focus, A, self.classname))
        return [lib.create_template(f"resolve{token_hex(4)}", body)]


@dataclass(frozen=True)
class GraphClassCardinality(GraphDiff):
    classname: URIRef
    expectedCount: int

    def reason(self) -> str:
        return f"Graph did not have {self.expectedCount} instances of {self.classname}"

    def resolve(self, lib: "Library") -> List["Template"]:
        templs = []
        for _ in range(self.expectedCount):
            template_body = Graph()
            template_body.add((PARAM["name"], A, self.classname))
            templs.append(lib.create_template(f"resolve{token_hex(4)}", template_body))
        return templs


@dataclass
class ValidationContext:
    """
    Holds the necessary information for processing the results of SHACL validation
    """

    shape_collections: List[ShapeCollection]
    valid: bool
    report: rdflib.Graph
    report_string: str
    model: "Model"

    @cached_property
    def diffset(self) -> Set[GraphDiff]:
        return self._report_to_diffset()

    @cached_property
    def _context(self) -> Graph:
        return sum((sc.graph for sc in self.shape_collections), start=Graph())  # type: ignore

    def as_templates(self) -> List["Template"]:
        return diffset_to_templates(self.diffset)

    def _report_to_diffset(self) -> Set[GraphDiff]:
        """
        Interpret a SHACL validation report and say what is missing.

        :return: A set of 'GraphDiff's that each abstract a SHACL shape violation
        :rtype: Set[GraphDiff]
        """
        classpath = SH["class"] | (SH.qualifiedValueShape / SH["class"])  # type: ignore
        shapepath = SH["node"] | (SH.qualifiedValueShape / SH["node"])  # type: ignore

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
            # otherwise, just append the body (use to_inline() to ensure
            # uniqueness of parameters)
            if "name" in templ.parameters:
                base.add_dependency(templ, {"name": "name"})
            else:
                base.body += templ.to_inline().body
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
