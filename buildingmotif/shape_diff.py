from collections import defaultdict
from dataclasses import dataclass
from secrets import token_hex
from typing import ClassVar, Dict, List, Optional, Set

from rdflib import Graph, URIRef

from buildingmotif.dataclasses import Library, Template
from buildingmotif.namespaces import CONSTRAINT, PARAM, SH, A
from buildingmotif.utils import _gensym


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


def process_shacl_validation_report(report: Graph, aux: Graph) -> List[Template]:
    """
    Interpret a SHACL validation report and say what is missing.

    Standard 'report' or 'diff' object:
    - focus node (could be the graph itself e.g. for cardinality constraints or an instance)
    - (path, class, mincount, maxcount)
    - (path, shape, mincount, maxcount)
    """
    classpath = SH["class"] | (SH.qualifiedValueShape / SH["class"])  # type: ignore
    shapepath = SH["node"] | (SH.qualifiedValueShape / SH["node"])  # type: ignore

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
            expected_count = g.value(result, SH.sourceShape / CONSTRAINT.exactCount)  # type: ignore
            of_class = g.value(result, SH.sourceShape / CONSTRAINT["class"])  # type: ignore
            diffs.add(GraphClassCardinality(focus, g, of_class, int(expected_count)))
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

    return diffset_to_templates(diffs)


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
