from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Dict, List, Optional, Set

import rdflib
from rdflib import Graph, URIRef

from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.namespaces import CONSTRAINT, SH
from buildingmotif.utils import get_template_parts_from_shape
from buildingmotif.validation import (
    GraphClassCardinality,
    GraphDiff,
    PathClassCount,
    PathShapeCount,
    RequiredClass,
    RequiredPath,
    diffset_to_templates,
)

if TYPE_CHECKING:
    from buildingmotif.dataclasses import Model, Template


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
