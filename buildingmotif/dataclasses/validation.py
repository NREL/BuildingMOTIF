from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from itertools import chain
from secrets import token_hex
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union

import rdflib
from rdflib import Graph, URIRef
from rdflib.term import Node

from buildingmotif import get_building_motif
from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.namespaces import CONSTRAINT, PARAM, SH, A
from buildingmotif.utils import _gensym, get_template_parts_from_shape, replace_nodes

if TYPE_CHECKING:
    from buildingmotif.dataclasses import Library, Model, Template


@dataclass(frozen=True)
class GraphDiff:
    """An abstraction of a SHACL Validation Result that can produce a template
    that resolves the difference between the expected and actual graph.

    Each GraphDiff has a 'focus' that is the node in the model that the
    GraphDiff is about. If 'focus' is None, then the GraphDiff is about the
    model itself rather than a specific node
    """

    # the node that failed (shape target)
    focus: Optional[URIRef]
    # the SHACL validation result graph corresponding to this failure
    validation_result: Graph
    graph: Graph

    def resolve(self, lib: "Library") -> List["Template"]:
        """Produces a list of templates to resolve this GraphDiff.

        :param lib: the library to hold the templates
        :type lib: Library
        :return: templates that reconcile the GraphDiff
        :rtype: List[Template]
        """
        raise NotImplementedError

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff."""
        raise NotImplementedError

    @cached_property
    def _result_uri(self) -> Node:
        """Return the 'name' of the ValidationReport to make failed_shape/failed_component
        easier to express. We compute this by taking advantage of the fact that the validation
        result graph is actually a tree with a single root. We can find the root by finding
        all URIs which appear as subjects in the validation_result graph that do *not* appear
        as objects; this should  be exactly one URI which is the 'root' of the validation result
        graph
        """
        possible_uris: Set[Node] = set(self.validation_result.subjects())
        objects: Set[Node] = set(self.validation_result.objects())
        sub_not_obj = possible_uris - objects
        if len(sub_not_obj) != 1:
            raise Exception(
                "Validation result has more than one 'root' node, which should not happen. Please raise an issue on https://github.com/NREL/BuildingMOTIF"
            )
        return sub_not_obj.pop()

    @cached_property
    def failed_shape(self) -> Optional[URIRef]:
        """The URI of the Shape that failed"""
        return self.validation_result.value(self._result_uri, SH.sourceShape)

    @cached_property
    def failed_component(self) -> Optional[URIRef]:
        """The Constraint Component of the Shape that failed"""
        return self.validation_result.value(
            self._result_uri, SH.sourceConstraintComponent
        )

    def __hash__(self):
        return hash(self.reason())


@dataclass(frozen=True)
class PathClassCount(GraphDiff):
    """Represents an entity missing paths to objects of a given type:
    $this <path> <object> .
    <object> a <classname> .
    """

    path: URIRef
    minc: Optional[int]
    maxc: Optional[int]
    classname: URIRef

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff."""
        return f"{self.focus} needs between {self.minc} and {self.maxc} instances of \
{self.classname} on path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """Produces a list of templates to resolve this GraphDiff.

        :param lib: the library to hold the templates
        :type lib: Library
        :return: templates that reconcile the GraphDiff
        :rtype: List[Template]
        """
        assert self.focus is not None
        body = Graph()
        for _ in range(self.minc or 0):
            inst = _gensym()
            body.add((self.focus, self.path, inst))
            body.add((inst, A, self.classname))
        return [lib.create_template(f"resolve_{token_hex(4)}", body)]


@dataclass(frozen=True, unsafe_hash=True)
class PathShapeCount(GraphDiff):
    """Represents an entity missing paths to objects that match a given shape.
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
        """Human-readable explanation of this GraphDiff."""
        return f"{self.focus} needs between {self.minc} and {self.maxc} instances of \
{self.shapename} on path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """Produces a list of templates to resolve this GraphDiff."""
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
    """Represents an entity missing a required property."""

    path: URIRef
    minc: Optional[int]
    maxc: Optional[int]

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff."""
        return f"{self.focus} needs between {self.minc} and {self.maxc} uses \
of path {self.path}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """Produces a list of templates to resolve this GraphDiff.

        :param lib: the library to hold the templates
        :type lib: Library
        :return: templates that reconcile the GraphDiff
        :rtype: List[Template]
        """
        assert self.focus is not None
        body = Graph()
        for _ in range(self.minc or 0):
            inst = _gensym()
            body.add((self.focus, self.path, inst))
        return [lib.create_template(f"resolve{token_hex(4)}", body)]


@dataclass(frozen=True)
class RequiredClass(GraphDiff):
    """Represents an entity that should be an instance of the class."""

    classname: URIRef

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff."""
        return f"{self.focus} needs to be a {self.classname}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """Produces a list of templates to resolve this GraphDiff.

        :param lib: the library to hold the templates
        :type lib: Library
        :return: templates that reconcile the GraphDiff
        :rtype: List[Template]
        """
        assert self.focus is not None
        body = Graph()
        body.add((self.focus, A, self.classname))
        return [lib.create_template(f"resolve{token_hex(4)}", body)]


@dataclass(frozen=True)
class GraphClassCardinality(GraphDiff):
    """Represents a graph that is missing an expected number of instances of
    the given class.
    """

    classname: URIRef
    expectedCount: int

    def reason(self) -> str:
        """Human-readable explanation of this GraphDiff."""
        return f"Graph did not have {self.expectedCount} instances of {self.classname}"

    def resolve(self, lib: "Library") -> List["Template"]:
        """Produces a list of templates to resolve this GraphDiff.

        :param lib: the library to hold the templates
        :type lib: Library
        :return: templates that reconcile the GraphDiff
        :rtype: List[Template]
        """
        templs = []
        for _ in range(self.expectedCount):
            template_body = Graph()
            template_body.add((PARAM["name"], A, self.classname))
            templs.append(lib.create_template(f"resolve{token_hex(4)}", template_body))
        return templs


@dataclass
class ValidationContext:
    """Holds the necessary information for processing the results of SHACL
    validation.
    """

    shape_collections: List[ShapeCollection]
    valid: bool
    report: rdflib.Graph
    report_string: str
    model: "Model"

    @cached_property
    def diffset(self) -> Dict[Optional[URIRef], Set[GraphDiff]]:
        """The unordered set of GraphDiffs produced from interpreting the input
        SHACL validation report.
        """
        return self._report_to_diffset()

    @cached_property
    def _context(self) -> Graph:
        return sum((sc.graph for sc in self.shape_collections), start=Graph())  # type: ignore

    def as_templates(self) -> List["Template"]:
        """Produces the set of templates that reconcile the GraphDiffs from the
        SHACL validation report.

        :return: reconciling templates
        :rtype: List[Template]
        """
        return diffset_to_templates(self.diffset)

    def get_reasons_with_severity(
        self, severity: Union[URIRef | str]
    ) -> Dict[Optional[URIRef], Set[GraphDiff]]:
        """
        Like diffset, but only includes ValidationResults with the given severity.
        Permitted values are:
        - SH.Violation or "Violation" for violations
        - SH.Warning or "Warning" for warnings
        - SH.Info or "Info" for info

        :param severity: the severity to filter by
        :type severity: Union[URIRef|str]
        :return: a dictionary of focus nodes to the reasons with the given severity
        :rtype: Dict[Optional[URIRef], Set[GraphDiff]]
        """

        if isinstance(severity, str):
            severity = SH[severity]

        # check if the severity is a valid SHACL severity
        if severity not in {SH.Violation, SH.Warning, SH.Info}:
            raise ValueError(
                f"Invalid severity: {severity}. Must be one of SH.Violation, SH.Warning, or SH.Info"
            )

        # for each value in the diffset, filter out the diffs that don't have the given severity
        # in the diffset.graph
        return {
            focus: {
                diff
                for diff in diffs
                if diff.validation_result.value(diff._result_uri, SH.resultSeverity)
                == severity
            }
            for focus, diffs in self.diffset.items()
        }

    def _report_to_diffset(self) -> Dict[Optional[URIRef], Set[GraphDiff]]:
        """Interpret a SHACL validation report and say what is missing.

        :return: a set of GraphDiffs that each abstract a SHACL shape violation
        :rtype: Set[GraphDiff]
        """
        classpath = SH["class"] | (SH.qualifiedValueShape / SH["class"])  # type: ignore
        shapepath = SH["node"] | (SH.qualifiedValueShape / SH["node"])  # type: ignore
        # TODO: for future use
        # proppath = SH["property"] | (SH.qualifiedValueShape / SH["property"])  # type: ignore

        g = self.report + self._context
        diffs: Dict[Optional[URIRef], Set[GraphDiff]] = defaultdict(set)
        for result in g.objects(predicate=SH.result):
            # check if the failure is due to our count constraint component
            focus = g.value(result, SH.focusNode)
            # get the subgraph corresponding to this ValidationReport -- see
            # https://www.w3.org/TR/shacl/#results-validation-result for details
            # on the structure and expected properties
            validation_report = g.cbd(result)
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
                diffs[None].add(
                    GraphClassCardinality(
                        None, validation_report, g, of_class, int(expected_count)
                    )
                )
            elif (
                g.value(result, SH.sourceConstraintComponent)
                == SH.ClassConstraintComponent
            ):
                requiring_shape = g.value(result, SH.sourceShape)
                expected_class = g.value(requiring_shape, SH["class"])
                diffs[focus].add(
                    RequiredClass(focus, validation_report, g, expected_class)
                )
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
                    diffs[focus].add(
                        PathClassCount(
                            focus,
                            validation_report,
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
                    diffs[focus].add(
                        PathShapeCount(
                            focus,
                            validation_report,
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
                    diffs[focus].add(
                        RequiredPath(
                            focus,
                            validation_report,
                            g,
                            path,
                            int(min_count) if min_count else None,
                            int(max_count) if max_count else None,
                        )
                    )
        return diffs


def diffset_to_templates(
    grouped_diffset: Dict[Optional[URIRef], Set[GraphDiff]]
) -> List["Template"]:
    """Combine GraphDiff by focus node to generate a list of templates that
    reconcile what is "wrong" with the Graph with respect to the GraphDiffs.

    :param diffset: a set of diffs produced by `_report_to_diffset`
    :type diffset: Set[GraphDiff]
    :return: list of templates that should resolve the SHACL violations when
        populated
    :rtype: List[Template]
    """
    from buildingmotif.dataclasses import Library, Template

    lib = Library.create(f"resolve_{token_hex(4)}")

    templates = []
    # now merge all tempaltes together for each focus node
    for focus, diffset in grouped_diffset.items():
        if focus is None:
            for diff in diffset:
                templates.extend(diff.resolve(lib))
            continue

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
