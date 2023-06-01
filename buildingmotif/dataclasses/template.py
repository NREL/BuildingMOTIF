import warnings
from collections import Counter
from dataclasses import dataclass
from itertools import chain
from secrets import token_hex
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Set, Tuple, Union

import rdflib
from rdflib.term import Node

from buildingmotif import get_building_motif
from buildingmotif.dataclasses.model import Model
from buildingmotif.namespaces import bind_prefixes
from buildingmotif.template_matcher import Mapping, TemplateMatcher
from buildingmotif.template_to_shape import template_to_nodeshape
from buildingmotif.utils import (
    PARAM,
    combine_graphs,
    copy_graph,
    remove_triples_with_node,
    replace_nodes,
)

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF
    from buildingmotif.dataclasses.library import Library


@dataclass
class Template:
    """This class mirrors :py:class`database.tables.DBTemplate`."""

    _id: int
    _name: str
    body: rdflib.Graph
    optional_args: List[str]
    _bm: "BuildingMOTIF"

    @classmethod
    def load(cls, id: int) -> "Template":
        """Load template from database.

        :param id: id of template
        :type id: int
        :return: loaded template
        :rtype: Template
        """
        bm = get_building_motif()
        db_template = bm.table_connection.get_db_template_by_id(id)
        body = bm.graph_connection.get_graph(db_template.body_id)

        return cls(
            _id=db_template.id,
            _name=db_template.name,
            optional_args=db_template.optional_args,
            body=body,
            _bm=bm,
        )

    def in_memory_copy(self) -> "Template":
        """Copy this template.

        :return: copy of this template
        :rtype: Template
        """
        return Template(
            _id=-1,
            _name=self._name,
            body=copy_graph(self.body, preserve_blank_nodes=False),
            optional_args=self.optional_args[:],
            _bm=self._bm,
        )

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, new_id):
        raise AttributeError("Cannot modify db id")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name: str) -> None:
        self._bm.table_connection.update_db_template_name(self._id, new_name)
        self._name = new_name

    def get_dependencies(self) -> Tuple["Dependency", ...]:
        """Get the template's dependencies.

        :return: a tuple of dependencies
        :rtype: Tuple
        """
        return tuple(
            [
                Dependency(dep.dependee_id, dep.args)
                for dep in self._bm.table_connection.get_db_template_dependencies(
                    self._id
                )
            ]
        )

    def add_dependency(self, dependency: "Template", args: Dict[str, str]) -> None:
        """Add dependency to template.

        :param dependency: dependency to add
        :type dependency: Template
        :param args: dictionary of dependency arguments
        :type args: Dict[str, str]
        """
        self._bm.table_connection.add_template_dependency_preliminary(
            self.id, dependency.id, args
        )

    def check_dependencies(self):
        """
        Verifies that all dependencies have valid references to the parameters
        in the dependency or (recursively) its dependencies. Raises an exception if any
        issues are found.

        It is recommended to call this after *all* templates in a library have been
        loaded in to the DB, else this might falsely raise an error.
        """
        for dep in self._bm.table_connection.get_db_template_dependencies(self.id):
            self._bm.table_connection.check_template_dependency_relationship(dep)

    def remove_dependency(self, dependency: "Template") -> None:
        """Remove dependency from template.

        :param dependency: dependency to remove
        :type dependency: Template
        """
        self._bm.table_connection.remove_template_dependency(self.id, dependency.id)

    @property
    def all_parameters(self) -> Set[str]:
        """The set of all parameters used in this template *including* its
        dependencies. Includes optional parameters.

        :return: set of parameters *with* dependencies
        :rtype: Set[str]
        """
        # handle local parameters first
        params = set(self.parameters)

        # then handle dependencies
        for dep in self.get_dependencies():
            params.update(dep.template.parameters)
        return params

    @property
    def parameters(self) -> Set[str]:
        """The set of all parameters used in this template *excluding* its
        dependencies. Includes optional parameters.

        :return: set of parameters *without* dependencies
        :rtype: Set[str]
        """
        # handle local parameters first
        nodes = chain.from_iterable(self.body.triples((None, None, None)))
        params = {str(p)[len(PARAM) :] for p in nodes if str(p).startswith(PARAM)}
        return params

    @property
    def dependency_parameters(self) -> Set[str]:
        """The set of all parameters used in this template's dependencies, including
        optional parameters.

        :return: set of parameters used in dependencies
        :rtype: Set[str]
        """
        params: Set[str] = set()
        for dep in self.get_dependencies():
            params = params.union(dep.template.parameters)
        return params

    @property
    def parameter_counts(self) -> Counter:
        """An addressable histogram of the parameter name counts in this
        template and all of its transitive dependencies.

        :return: count of parameters
        :rtype: Counter
        """
        counts: Counter = Counter()
        counts.update(self.parameters)
        for dep in self.get_dependencies():
            counts.update(dep.template.parameter_counts)
        return counts

    # TODO: method to get the 'types' of the parameters

    def dependency_for_parameter(self, param: str) -> Optional["Template"]:
        """Returns the dependency that uses the given parameter if one exists.

        :param param: parameter to search for
        :type param: str
        :return: dependency that uses the given parameter
        :rtype: Optional[Template]
        """
        for dep in self.get_dependencies():
            if param in dep.args.values():
                return dep.template
        return None

    def to_inline(self, preserve_args: Optional[List[str]] = None) -> "Template":
        """Return an inline-able copy of this template.

        Suffixes all parameters with a unique identifier that will avoid
        parameter name collisions when templates are combined with one another.
        Any argument names in the `preserve_args` list will not be adjusted.

        :param preserve_args: parameters whose names will be preserved,
            defaults to None
        :type preserve_args: Optional[List[str]], optional
        :return: a template with globally unique parameters
        :rtype: Template
        """
        templ = self.in_memory_copy()
        suffix = f"{token_hex(4)}-inlined"
        # the lookup table of old to new parameter names
        to_replace = {}
        for param in templ.parameters:
            # skip if (a) we want to preserve the param or (b) it is already inlined
            if (preserve_args and param in preserve_args) or (
                param.endswith("-inlined")
            ):
                continue
            param = PARAM[param]
            to_replace[param] = rdflib.URIRef(f"{param}-{suffix}")
        replace_nodes(templ.body, to_replace)
        return templ

    def inline_dependencies(self) -> "Template":
        """Copies this template with all dependencies recursively inlined.

        Parameters of dependencies will be renamed to avoid confusion.

        :return: copy of this template with all dependencies inlined
        :rtype: Template
        """
        templ = self.in_memory_copy()
        # if this template has no dependencies, then return unaltered
        if not self.get_dependencies():
            return templ

        # start with this template's parameters; this recurses into each
        # dependency to inline dependencies
        for dep in self.get_dependencies():
            # get the inlined version of the dependency
            deptempl = dep.template.inline_dependencies()

            # replace dependency parameters with the names they inherit
            # through the provided bindings
            rename_params: Dict[str, str] = {
                ours: theirs for ours, theirs in dep.args.items()
            }
            # replace all parameters *not* mentioned in the args by prefixing
            # them with the 'name' parameter binding; this is guaranteed
            # to exist
            name_prefix = dep.args.get("name")
            # for each parameter in the dependency...
            for param in deptempl.parameters:
                # if it does *not* have a mapping in the dependency, then
                # prefix the parameter with the value of the 'name' binding
                # to scope it properly
                if param not in dep.args and param != "name":
                    rename_params[param] = f"{name_prefix}-{param}"

            # replace the parameters in the dependency template
            replace_nodes(
                deptempl.body, {PARAM[k]: PARAM[v] for k, v in rename_params.items()}
            )

            templ_optional_args = set(templ.optional_args)
            # figure out which of deptempl's parameters are encoded as 'optional' by the
            # parent (depending) template
            deptempl_opt_args = deptempl.parameters.intersection(templ.optional_args)
            # if the 'name' of the deptempl is optional, then all the arguments inside deptempl
            # become optional
            if rename_params["name"] in deptempl_opt_args:
                # mark all of deptempl's parameters as optional
                templ_optional_args.update(deptempl.parameters)
            else:
                # otherwise, only add the parameters that are explicitly
                # marked as optional *and* appear in this dependency
                templ_optional_args.update(deptempl_opt_args)
            # ensure that the optional_args includes all params marked as
            # optional by the dependency
            templ_optional_args.update(
                [rename_params[n] for n in deptempl.optional_args]
            )

            # convert our set of optional params to a list and assign to the parent template
            templ.optional_args = list(templ_optional_args)

            # append the inlined template into the parent's body
            templ.body += deptempl.body

        return templ

    def evaluate(
        self,
        bindings: Dict[str, Node],
        namespaces: Optional[Dict[str, rdflib.Namespace]] = None,
        require_optional_args: bool = False,
        warn_unused: bool = True,
    ) -> Union["Template", rdflib.Graph]:
        """Evaluate the template with the provided bindings.

        If all parameters in the template have a provided binding, then a graph
        will be returned. Otherwise, a new Template will be returned that
        incorporates the provided bindings and preserves unbound parameters. If
        `require_optional_args` is True, then the template evaluation will not
        return a graph unless all optional arguments are bound. If
        `require_optional_args` is False, then the template evaluation will
        return a graph even if some optional arguments are unbound.

        :param bindings: map of parameter {name: RDF term} to substitute
        :type bindings: Dict[str, Node]
        :param namespaces: namespace bindings to add to the graph,
            defaults to None
        :type namespaces: Optional[Dict[str, rdflib.Namespace]], optional
        :param require_optional_args: whether to require all optional arguments
            to be bound, defaults to False
        :type require_optional_args: bool
        :param warn_unused: if True, print a warning if there were any parameters left
            unbound during evaluation. If 'require_optional_args' is True,
            then this will consider optional parameters when producing the warning;
            otherwise, optional paramters will be ignored; defaults to True
        :type warn_unused: bool
        :return: either a template or a graph, depending on whether all
            parameters were provided
        :rtype: Union[Template, rdflib.Graph]
        """
        templ = self.in_memory_copy()
        # put all of the parameter names into the PARAM namespace so they can be
        # directly subsituted in the template body
        uri_bindings: Dict[Node, Node] = {PARAM[k]: v for k, v in bindings.items()}
        # replace the param:<name> URIs in the template body with the bindings
        # provided in the call to evaluate()
        replace_nodes(templ.body, uri_bindings)
        leftover_params = (
            templ.parameters.difference(bindings.keys())
            if not require_optional_args
            else (templ.parameters.union(self.optional_args)).difference(
                bindings.keys()
            )
        )
        # true if all parameters are now bound or only optional args are unbound
        if len(templ.parameters) == 0 or (
            not require_optional_args and templ.parameters == set(self.optional_args)
        ):
            bind_prefixes(templ.body)
            if namespaces:
                for prefix, namespace in namespaces.items():
                    templ.body.bind(prefix, namespace)
            if not require_optional_args:
                # remove all triples that touch unbound optional_args
                unbound_optional_args = set(templ.optional_args) - set(bindings.keys())
                for arg in unbound_optional_args:
                    remove_triples_with_node(templ.body, PARAM[arg])
            return templ.body
        if len(leftover_params) > 0 and warn_unused:
            warnings.warn(
                f"Parameters \"{', '.join(leftover_params)}\" were not provided during evaluation"
            )
        return templ

    def fill(
        self, ns: rdflib.Namespace, include_optional: bool = False
    ) -> Tuple[Dict[str, Node], rdflib.Graph]:
        """Evaluates the template with autogenerated bindings within the given
        namespace.

        :param ns: namespace to contain the autogenerated entities
        :type ns: rdflib.Namespace
        :param include_optional: if True, invent URIs for optional parameters; ignore if False
        :type include_optional: bool
        :return: a tuple of the bindings used and the resulting graph
        :rtype: Tuple[Dict[str, Node], rdflib.Graph]
        """
        bindings: Dict[str, Node] = {
            param: ns[f"{param}_{token_hex(4)}"]
            for param in self.parameters
            if include_optional or param not in self.optional_args
        }
        res = self.evaluate(bindings)
        if not isinstance(res, rdflib.Graph):
            raise ValueError(
                f"Expected graph but got template after call to evaluate(). Missing params: {res.parameters}"
            )
        assert isinstance(res, rdflib.Graph)
        return bindings, res

    @property
    def defining_library(self) -> "Library":
        """The library defining this template.

        :return: library
        :rtype: Library
        """
        from buildingmotif.dataclasses.library import Library

        return Library.load(
            self._bm.table_connection.get_library_defining_db_template(self.id).id
        )

    def library_dependencies(self) -> List["Library"]:
        """Get library dependencies for this template.

        :return: list of libraries
        :rtype: List[Library]
        """
        from buildingmotif.dataclasses.library import Library

        libs = {self.defining_library.id}
        for dep in self.get_dependencies():
            libs.add(dep.template.defining_library.id)
        return [Library.load(id) for id in libs]

    def find_subgraphs(
        self, model: Model, *ontologies: rdflib.Graph
    ) -> Generator[Tuple[Mapping, rdflib.Graph, Optional["Template"]], None, None]:
        """Produces an iterable of subgraphs in the model that are partially or
        entirely covered by the provided template.

        :yield: iterable of subgraphs in the model
        :rtype: Generator[Tuple[Mapping, rdflib.Graph, Optional[Template]], None, None]
        """
        # TODO: can we figure out what ontology to use automatically?
        # if ontology is not specified, pull in all shapes related to this template's library
        # and all of its dependencies
        if len(ontologies) == 0:
            ontology = rdflib.Graph()
            for lib in self.library_dependencies():
                ontology += lib.get_shape_collection().graph
        else:
            ontology = combine_graphs(*ontologies)

        matcher = TemplateMatcher(model.graph, self, ontology)
        for mapping, sg in matcher.building_mapping_subgraphs_iter():
            yield mapping, sg, matcher.remaining_template(mapping)

    def to_nodeshape(self) -> rdflib.Graph:
        """
        Interprets the template body as a SHACL shape and returns the SHACL
        shape in its own graph. See buildingmotif.template_to_shape.template_to_nodeshape
        for the specific translation rules and implementation.

        :return: a graph containing the NodeShape
        :rtype: rdflib.Graph
        """
        return template_to_nodeshape(self)


@dataclass
class Dependency:
    """Dependency"""

    _template_id: int
    args: Dict[str, str]

    @property
    def template_id(self):
        return self._template_id

    @property
    def template(self) -> Template:
        return Template.load(self._template_id)
