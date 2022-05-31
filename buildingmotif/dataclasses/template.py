# pylama:ignore=E203
from dataclasses import dataclass
from itertools import chain
from secrets import token_hex
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union

import rdflib

from buildingmotif.namespaces import bind_prefixes
from buildingmotif.utils import (
    PARAM,
    Term,
    copy_graph,
    get_building_motif,
    replace_nodes,
)

if TYPE_CHECKING:
    from buildingmotif.building_motif import BuildingMotif


@dataclass
class Template:
    """Template. This class mirrors DBTemplate."""

    _id: int
    _name: str
    _head: Tuple[str, ...]
    body: rdflib.Graph
    _bm: "BuildingMotif"

    @classmethod
    def load(cls, id: int) -> "Template":
        """load Template from db

        :param id: id of template
        :type id: int
        :return: loaded Template
        :rtype: Template
        """
        bm = get_building_motif()
        db_template = bm.table_connection.get_db_template(id)
        body = bm.graph_connection.get_graph(db_template.body_id)

        return cls(
            _id=db_template.id,
            _name=db_template.name,
            _head=db_template.head,
            body=body,
            _bm=bm,
        )

    def copy(self) -> "Template":
        """
        Return a copy of this template.
        """
        return Template(
            _id=-1,
            _name=self._name,
            _head=self._head,
            body=copy_graph(self.body),
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

    @property
    def head(self):
        return self._head

    @head.setter
    def head(self, _: str) -> None:
        raise AttributeError("Cannot modify head")

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
    def parameters(self) -> Set[str]:
        """
        The set of all parameters used in this template, including its dependencies
        """
        # handle local parameters first
        nodes = chain.from_iterable(self.body.triples((None, None, None)))
        params = {str(p)[len(PARAM) :] for p in nodes if str(p).startswith(PARAM)}

        # then handle dependencies
        for dep in self.get_dependencies():
            params.update(dep.template.parameters)
        return params

    def dependency_for_parameter(self, param: str) -> Optional["Template"]:
        """
        Returns the dependency that uses the given parameter if one exists.
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
        """
        templ = self.copy()
        sfx = f"{token_hex(4)}"
        for param in templ.parameters:
            if (preserve_args and param in preserve_args) or (
                param.endswith("-inlined")
            ):
                continue
            param = PARAM[param]
            replace_nodes(templ.body, {param: rdflib.URIRef(f"{param}-{sfx}-inlined")})
        return templ

    def inline_dependencies(self) -> "Template":
        """
        Returns a copy of this template with all dependencies recursively inlined
        """
        templ = self.copy()
        if not self.get_dependencies():
            return templ

        for dep in self.get_dependencies():
            inlined_dep = dep.template.inline_dependencies()
            # concat bodies
            templ.body += inlined_dep.to_inline().body
            # concat heads
            old_head = list(templ._head)
            old_head.extend(inlined_dep.head)
            templ._head = tuple(set(old_head))

        return templ

    def evaluate(
        self,
        bindings: Dict[str, Term],
        namespaces: Optional[Dict[str, rdflib.Namespace]] = None,
    ) -> Union["Template", rdflib.Graph]:
        """
        Evaluate the template with the provided bindings. If all parameters in the template
        have a provided binding, then a Graph will be returend. Otherwise, a new Template
        will be returned which incorporates the provided bindings and preserves unbound
        parameters.
        """
        templ = self.copy()
        uri_bindings = {PARAM[k]: v for k, v in bindings.items()}
        replace_nodes(templ.body, uri_bindings)
        print(uri_bindings, templ.parameters)
        # true if all parameters are now bound
        if len(templ.parameters) == 0:
            bind_prefixes(templ.body)
            if namespaces:
                for prefix, namespace in namespaces.items():
                    templ.body.bind(prefix, namespace)
            return templ.body
        # remove bound 'head' parameters
        templ._head = tuple(set(templ._head) - set(bindings.keys()))
        return templ

    def fill(self, ns: rdflib.Namespace) -> Tuple[Dict[str, Term], rdflib.Graph]:
        """
        Evaluates the template with autogenerated bindings w/n the given 'ns' namespace.
        Returns a dictionary of the bindings and the resulting graph
        """
        bindings = {param: ns[f"{param}_{token_hex(4)}"] for param in self.parameters}
        res = self.evaluate(bindings)
        assert isinstance(res, rdflib.Graph)
        return bindings, res


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
