from collections import Counter
from dataclasses import dataclass
from itertools import chain
from secrets import token_hex
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Set, Tuple, Union

import rdflib

from buildingmotif import get_building_motif
from buildingmotif.dataclasses.model import Model
from buildingmotif.namespaces import bind_prefixes
from buildingmotif.template_matcher import Mapping, TemplateMatcher
from buildingmotif.utils import (
    PARAM,
    Term,
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
    """Template. This class mirrors DBTemplate."""

    _id: int
    _name: str
    body: rdflib.Graph
    optional_args: List[str]
    _bm: "BuildingMOTIF"

    @classmethod
    def load(cls, id: int) -> "Template":
        """load Template from db

        :param id: id of template
        :type id: int
        :return: loaded Template
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
        """
        Return a copy of this template.
        """
        return Template(
            _id=-1,
            _name=self._name,
            body=copy_graph(self.body),
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
        return tuple(
            [
                Dependency(dep.dependee_id, dep.args)
                for dep in self._bm.table_connection.get_db_template_dependencies(
                    self._id
                )
            ]
        )

    def add_dependency(self, dependency: "Template", args: Dict[str, str]) -> None:
        self._bm.table_connection.add_template_dependency(self.id, dependency.id, args)

    def remove_dependency(self, dependency: "Template") -> None:
        self._bm.table_connection.remove_template_dependency(self.id, dependency.id)

    @property
    def all_parameters(self) -> Set[str]:
        """
        The set of all parameters used in this template, including its dependencies
        """
        # handle local parameters first
        params = set(self.parameters)

        # then handle dependencies
        for dep in self.get_dependencies():
            params.update(dep.template.parameters)
        return params

    @property
    def parameters(self) -> Set[str]:
        """
        The set of all parameters used in this template, *not* including its dependencies
        """
        # handle local parameters first
        nodes = chain.from_iterable(self.body.triples((None, None, None)))
        params = {str(p)[len(PARAM) :] for p in nodes if str(p).startswith(PARAM)}
        return params

    @property
    def parameter_counts(self) -> Counter:
        """
        An addressable histogram of the parameter name counts in this template +
        all of its transitive dependencies.
        """
        counts: Counter = Counter()
        counts.update(self.parameters)
        for dep in self.get_dependencies():
            counts.update(dep.template.parameter_counts)
        return counts

    # TODO: method to get the 'types' of the parameters

    def dependency_for_parameter(self, param: str) -> Optional["Template"]:
        """
        Returns the dependency that uses the given parameter if one exists.

        :param param: parameter to search for
        :type param: str
        :return: dependency which uses the given parameter
        :rtype: Optional["Template"]
        """
        for dep in self.get_dependencies():
            if param in dep.args.values():
                return dep.template
        return None

    def to_inline(self, preserve_args: Optional[List[str]] = None) -> "Template":
        """
        Return an inline-able copy of this template by suffixing all parameters
        with a unique identifier which will avoid parameter name collisions when templates
        are combined with one another. Any argument names in the preserve_args list will
        not be adjusted

        :param preserve_args: parameters whose names will be preserved, defaults to None
        :type preserve_args: Optional[List[str]], optional
        :return: a template w/ globally unique parameters
        :rtype: "Template"
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
        """
        Returns a copy of this template with all dependencies recursively inlined.
        Parameters of dependencies will be renamed to avoid confusion..

        :return: copy of this template with all dependencies inlined
        :rtype: "Template"
        """
        templ = self.in_memory_copy()
        # if this template has no dependencies, then return unaltered
        if not self.get_dependencies():
            return templ

        # count of parameters in this template + all dependencies
        counts = self.parameter_counts
        # start with this template's parameters; if there is
        for dep in self.get_dependencies():
            # get the inlined version of the dependency
            deptempl = dep.template.inline_dependencies()
            # replace dependency parameters with the names they inherit
            # through the provided bindings
            rename_args: Dict[rdflib.URIRef, Term] = {
                PARAM[ours]: PARAM[theirs] for ours, theirs in dep.args.items()
            }
            replace_nodes(deptempl.body, rename_args)
            # find the parameters in the dependency that also appear in other templates:
            # the conflicted parameters are those that appear in the 'rest' of the parameters
            # (gien by params_without_dep) *and* don't have their conflicting name as a result
            # of the parameter bindings (dep.args.values())
            dep_counts = deptempl.parameter_counts
            params_without_dep = set(counts - dep_counts)
            conflicted = params_without_dep.intersection(dep_counts.keys()) - set(
                dep.args.values()
            )
            # replace conflicted parameters
            # get the name of the entity this dependency will be bound to via the 'name'
            # parameter, defaulting to the name of the dependee template
            bound_name = dep.args.get("name", deptempl.name)
            conflicted_params: Dict[rdflib.URIRef, Term] = {
                PARAM[conflicted_param]: PARAM[f"{bound_name}-{conflicted_param}"]
                for conflicted_param in conflicted
            }
            # update the template's body w/ the new renamed parameters
            replace_nodes(deptempl.body, conflicted_params)
            # concatenate the dependency's body with this template's body
            templ.body += deptempl.body

        return templ

    def evaluate(
        self,
        bindings: Dict[str, Term],
        namespaces: Optional[Dict[str, rdflib.Namespace]] = None,
        require_optional_args: bool = False,
    ) -> Union["Template", rdflib.Graph]:
        """
        Evaluate the template with the provided bindings. If all parameters in the template
        have a provided binding, then a Graph will be returned. Otherwise, a new Template
        will be returned which incorporates the provided bindings and preserves unbound
        parameters. If require_optional_args is True, then the template evaluation will not return
        a Graph unless all optional arguments are bound. If require_optional_args is False, then
        the template evaluation will return a Graph even if some optional arguments are unbound.

        :param bindings: map of parameter name -> RDF term to substitute
        :type bindings: Dict[str, Term]
        :param namespaces: namespace bindings to add to the graph, defaults to None
        :type namespaces: Optional[Dict[str, rdflib.Namespace]], optional
        :param require_optional_args: whether to require all optional arguments to be bound,
                defaults to False
        :type require_optional_args: bool
        :return: either a template or a graph, depending on whether all parameters were provided
        :rtype: Union["Template", rdflib.Graph]
        """
        templ = self.in_memory_copy()
        uri_bindings = {PARAM[k]: v for k, v in bindings.items()}
        replace_nodes(templ.body, uri_bindings)
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
                unbound_optional_args = set(templ.optional_args) - set(
                    uri_bindings.keys()
                )
                for arg in unbound_optional_args:
                    remove_triples_with_node(templ.body, PARAM[arg])
            return templ.body
        return templ

    def fill(self, ns: rdflib.Namespace) -> Tuple[Dict[str, Term], rdflib.Graph]:
        """
        Evaluates the template with autogenerated bindings w/n the given "ns" namespace.

        :param ns: namespace to contain the autogenerated entities
        :type ns: rdflib.Namespace
        :return: a tuple of the bindings used and the resulting graph
        :rtype: Tuple[Dict[str, Term], rdflib.Graph]
        """
        bindings = {param: ns[f"{param}_{token_hex(4)}"] for param in self.parameters}
        res = self.evaluate(bindings)
        assert isinstance(res, rdflib.Graph)
        return bindings, res

    @property
    def defining_library(self) -> "Library":
        from buildingmotif.dataclasses.library import Library

        return Library.load(
            self._bm.table_connection.get_library_defining_db_template(self.id).id
        )

    def library_dependencies(self) -> List["Library"]:
        from buildingmotif.dataclasses.library import Library

        libs = {self.defining_library.id}
        for dep in self.get_dependencies():
            libs.add(dep.template.defining_library.id)
        return [Library.load(id) for id in libs]

    def find_subgraphs(
        self, model: Model, *ontologies: rdflib.Graph
    ) -> Generator[Tuple[Mapping, rdflib.Graph, Optional["Template"]], None, None]:
        """
        Produces an iterable of subgraphs in the model that are partially or entirely
        covered by the provided template.
        # TODO: can we figure out what ontology to use automatically?
        """
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
            print(mapping)
            print(sg.serialize())
            print("*" * 80)
            yield mapping, sg, matcher.remaining_template(mapping)


@dataclass
class Dependency:
    _template_id: int
    args: Dict[str, str]

    @property
    def template_id(self):
        return self._template_id

    @property
    def template(self) -> Template:
        return Template.load(self._template_id)
