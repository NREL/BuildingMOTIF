from collections import defaultdict
from copy import copy
from pathlib import Path
from secrets import token_hex
from string import Formatter
from typing import Dict, List, Optional, Set, Tuple, Union

import yaml  # type: ignore
from rdflib import Graph, Namespace
from rdflib.term import BNode, Literal, URIRef

from building_motif.utils import new_temporary_graph, template_to_shape

PREAMBLE = """@prefix bacnet: <http://data.ashrae.org/bacnet/2020#> .
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix bsh: <https://brickschema.org/schema/BrickShape#> .
@prefix dcterms: <http://purl.org/dc/terms#> .
@prefix ifc: <https://brickschema.org/extension/ifc#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix qudtqk: <http://qudt.org/vocab/quantitykind/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sdo: <http://schema.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix tag: <https://brickschema.org/schema/BrickTag#> .
@prefix unit: <http://qudt.org/vocab/unit/> .
@prefix vcard: <http://www.w3.org/2006/vcard/ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""

Term = Union[Literal, BNode, URIRef]


class Template:
    """
    A template is a function that takes a set of parameters and returns a graph.
    """

    def __init__(
        self,
        library: Optional["TemplateLibrary"],
        name: str,
        head: List[str],
        body: str,
        deps: Dict[str, List[str]],
    ) -> None:
        self.name = name
        self.head = head
        self.body = body
        self.deps = deps
        self.library = library

    @property
    def parameters(self) -> Set[str]:
        """
        The set of all parameters used in this template, including its dependencies.
        """
        params = {fname for _, fname, _, _ in Formatter().parse(self.body) if fname}
        # pull in the parameters for all dependencies....hope there are no loops!
        # TODO: handle or detect circular dependencies
        if not len(self.deps):
            return params
        assert self.library is not None, "Cannot inline dependencies without a library."
        for dep_name in self.deps.keys():
            # TODO: handle list
            dep = self.library[dep_name][0]
            params.update(dep.parameters)
        return params

    @property
    def dependency_parameters(self) -> Set[str]:
        """
        The set of parameters used in the dependencies of this template.
        """
        params: Set[str] = set()
        # TODO: handle or detect circular dependencies
        if not len(self.deps):
            return params
        assert self.library is not None, "Cannot inline dependencies without a library."
        for dep_name, dep_args in self.deps.items():
            params = params.union(dep_args)
            # TODO: handle list
            dep = self.library[dep_name][0]
            params.update(dep.parameters)
            params.update(dep.dependency_parameters)
        return params

    def dependency_for_parameter(self, param: str) -> Optional["Template"]:
        """
        Returns the dependency that uses the given parameter if one exists.
        """
        assert self.library is not None, "Cannot fetch dependencies without a library."
        for dep_name, dep_args in self.deps.items():
            if param in dep_args:
                return self.library[dep_name][0]
        return None

    def to_inline(self, preserve_args: List[str]) -> "Template":
        """
        Return an inline-able version of this template with a unique
        name prefix to avoid name collisions. Preserve names of
        any arguments that are passed in.
        """
        inlined_templ = copy(self)
        pfx = f"{self.name}-{token_hex(8)}"
        for param in self.parameters:
            if param not in preserve_args:
                inlined_templ.body = self.body.replace(
                    f"{{{param}}}", f"{{{pfx}_{param}}}"
                )
        return inlined_templ

    def inline_dependencies(self) -> None:
        """
        Transforms the template by inlining all of its dependencies (this happens recursively).
        """
        if not len(self.deps):
            return
        assert self.library is not None, "Cannot inline dependencies without a library."
        for dep_name, dep_args in self.deps.items():
            # TODO: handle list
            dep_templ = copy(self.library[dep_name][0])
            dep_templ.inline_dependencies()

            # map the parameters: the callee (dep_templ.parameters) args need to be replaced
            # with the caller (dep_args) args. Use "None" to offset
            # callee arg -> caller arg
            mapping = {}
            callee_args = dep_templ.head
            for idx, caller_arg in enumerate(dep_args):
                if caller_arg is None:
                    continue
                mapping[callee_args[idx]] = caller_arg
            for callee, caller in mapping.items():
                dep_templ.body = dep_templ.body.replace(
                    f"{{{callee}}}", f"{{{caller}}}"
                )
            dep_templ = dep_templ.to_inline(list(mapping.values()))

            self.head += dep_templ.head
            self.body += "\n" + dep_templ.body
            self.deps.update(dep_templ.deps)
        # erase all deps -- they are resolved!
        self.deps = {}

    def evaluate(
        self, bindings: Dict[str, Term], more_namespaces: Optional[dict] = None
    ) -> Union["Template", Graph]:
        """
        Evaluate the template with as many bindings as are provided.
        """
        all_bindings = {param: f"{{{param}}}" for param in self.parameters}
        for param, value in bindings.items():
            all_bindings[param] = value.n3()

        # if all of the parameters have been bound then produce a serialized graph
        # and then parse it to an rdflib.Graph
        if len(bindings) == len(self.parameters):
            g = new_temporary_graph(more_namespaces)
            if more_namespaces:
                preamble = PREAMBLE + "\n".join(
                    f"@prefix {prefix}: <{uri}> .\n"
                    for prefix, uri in more_namespaces.items()
                )
            else:
                preamble = PREAMBLE
            data = preamble + self.body.format(**all_bindings)
            g.parse(data=data, format="ttl")
            return g

        # if *not* all of the parameters have been bound, then produce a new template
        # with the provided elements filled in
        partial = copy(self)
        partial.body = self.body.format(**all_bindings)
        partial.head = [x for x in self.head if x not in bindings.keys()]
        return partial

    def fill_in(self, bldg: Namespace) -> Tuple[Dict[str, Term], Graph]:
        """
        Evaluates the template with autogenerated bindings within the given namespace.
        Returns a dictionary of the bindings and the resulting graph.
        """
        bindings = {param: bldg[f"{param}_{token_hex(8)}"] for param in self.parameters}
        res = self.evaluate(bindings, {"bldg": bldg})
        assert isinstance(res, Graph)
        return bindings, res

    def __repr__(self) -> str:
        return f"Template({self.name})"


class TemplateLibrary:
    """
    A group of templates defined in a file. Supports basic lookups via __getitem__ and
    can convert included templates to SHACL shapes.
    """

    def __init__(self, filename: Union[str, Path]) -> None:
        self.templates = self._load_template_file(filename)

    def __getitem__(self, key: str) -> List[Template]:
        return self.templates[key]

    def __repr__(self) -> str:
        return f"TemplateLibrary({self.templates})"

    def _load_template_file(
        self, filename: Union[str, Path]
    ) -> Dict[str, List[Template]]:
        """
        Returns list of Template objects defined in the file.
        """
        ret = defaultdict(list)
        with open(filename, "r") as f:
            data = yaml.load(f, yaml.Loader)
            for templ in data:
                for name, defn in templ.items():
                    deps = {d["rule"]: d["args"] for d in defn.pop("dependencies", [])}
                    templ[name]["deps"] = deps
                name, defn = templ.popitem()
                templ = Template(self, name, **defn)
                ret[templ.name].append(templ)
        return ret

    def get_shacl_shapes(self) -> Graph:
        """
        Returns a graph containing the SHACL shape corresponding to each
        template defined in the library.
        """
        MARK = Namespace("urn:___mark___#")
        full_graph = new_temporary_graph({"mark": MARK})
        for templates in self.templates.values():
            for template in templates:
                full_graph += template_to_shape(template)
        return full_graph


def dump(
    templ: Template,
    params: Dict[str, Term],
    more_namespaces: Optional[Dict[str, Namespace]] = None,
) -> None:
    """
    Dump the contents of the templates as a Graph. Helpful for debugging.
    """
    templ.inline_dependencies()
    if params:
        res = templ.evaluate(params, more_namespaces)
    else:
        _, res = templ.fill_in(Namespace("https://example.org/bldg"))
    if isinstance(res, Graph):
        print(res.serialize(format="ttl"))
        print("ALL DONE!")
    else:
        print(
            f"original params ({len(templ.parameters)}): {templ.parameters}"
            "\nnow have ({len(res.parameters)}): {res.parameters}"
        )
