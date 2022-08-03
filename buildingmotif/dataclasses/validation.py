from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
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

    @property
    def diffset(self) -> Set[GraphDiff]:
        return self._report_to_diffset()

    @property
    def _context(self) -> Graph:
        return reduce(sum, (sc.graph for sc in self.shape_collections))

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
                    result, SH.sourceShape / CONSTRAINT.exactCount
                )  # type: ignore
                of_class = g.value(result, SH.sourceShape / CONSTRAINT["class"])  # type: ignore
                diffs.add(
                    GraphClassCardinality(focus, g, of_class, int(expected_count))
                )
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
    lib = Library.create("resolve")
    # compute the GROUP BY GraphDiff.focus
    for diff in diffset:
        related[diff.focus].add(diff)

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
        unified_evaluated = unified.evaluate({"name": focus})
        assert isinstance(unified_evaluated, Template)
        templates.append(unified_evaluated)
    return templates
