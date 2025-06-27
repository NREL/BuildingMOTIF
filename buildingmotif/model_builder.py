import secrets
import re
from urllib.parse import quote
from typing import Dict, List, Optional, Union

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.store import Store
from rdflib.term import Node

from buildingmotif.dataclasses import Library, Template
from buildingmotif.namespaces import PARAM, RDF, RDFS


class TemplateBuilderContext(Graph):
    """
    A context for building templates. This class allows the user to
    add templates to the context and then access them by name. The
    context also allows the user to compile all of the templates in
    the context into a single graph.
    """

    def __init__(self, ns: Namespace, store: Optional[Union[Store, str]] = None):
        """
        Creates a new TemplateBuilderContext. The context will create
        entities in the given namespace.

        :param ns:  The namespace to use for the context
        :param store: An optional backing store for the graph; ok to leave blank unless
                    you are experiencing performance issues using TemplateBuilderContext
        """
        self.templates: Dict[str, Template] = {}
        self.wrappers: List[TemplateWrapper] = []
        self.ns: Namespace = ns
        super(TemplateBuilderContext, self).__init__(
            store=store or "default", identifier=None
        )

    def add_template(self, template: Template):
        """
        Adds a template to the context with all of its dependencies
        inlined. Allows the user of the context to access the template
        by name.

        :param template: The template to add to the context
        """
        self.templates[template.name] = template.inline_dependencies()

    def add_templates_from_library(self, library: Library):
        """
        Adds all of the templates from a library to the context

        :param library: The library to add to the context
        """
        for template in library.get_templates():
            self.add_template(template)

    def __getitem__(self, template_name):
        if template_name in self.templates:
            w = TemplateWrapper(self.templates[template_name], self.ns)
            self.wrappers.append(w)
            return w
        else:
            raise KeyError(f"Invalid template name: {template_name}")

    def compile(self) -> Graph:
        """
        Compiles all of the template wrappers and concatenates them into a single Graph

        :return: A graph containing all of the compiled templates
        """
        graph = Graph()
        graph += self
        for wrapper in self.wrappers:
            graph += wrapper.compile()
        # add a label to every instance if it doesn't have one. Make
        # the label the same as the value part of the URI
        for s, o in graph.subject_objects(predicate=RDF.type):
            if (s, RDFS.label, None) not in graph:
                # get the 'value' part of the o URI using qname
                _, _, value = graph.namespace_manager.compute_qname(str(o))
                graph.add((s, RDFS.label, Literal(value)))
        return graph


class TemplateWrapper:
    def __init__(self, template: Template, ns: Namespace):
        """
        Creates a new TemplateWrapper. The wrapper is used to bind
        parameters to a template and then compile the template into
        a graph.

        :param template: The template to wrap
        :param ns: The namespace to use for the wrapper; all bindings will be added to this namespace
        """
        self.template = template
        self.bindings: Dict[str, Node] = {}
        self.ns = ns
        self.variadic_parameters: set[str] = set()

    def __call__(self, **kwargs):
        for k, v in kwargs.items():
            self[k] = v
        return self

    def __getitem__(self, param):
        if self._is_variadic(param):
            # use a fresh parameter
            param = self._get_fresh_variadic(param)
        elif param in self.bindings:
            return self.bindings[param]
        elif param not in self.template.all_parameters:
            raise KeyError(f"Invalid parameter: {param}")
        # if the param is not bound, then invent a name
        # by prepending the parameter name to a random string
        self.bindings[param] = self.ns[param + "_" + secrets.token_hex(4)]
        return self.bindings[param]

    def __setitem__(self, param, value):
        if self._is_variadic(param):
            # if the parameter is variadic, then we need to
            # create a new parameter name for each value
            param = self._get_fresh_variadic(param)
        elif param not in self.template.all_parameters:
            raise KeyError(f"Invalid parameter: {param}")
        # if value is not a URIRef, Literal or BNode, then put it in the namespace
        if not isinstance(value, (URIRef, Literal, BNode)):
            value = self.ns[value]
        # check datatype of value is URIRef, Literal or BNode
        if not isinstance(value, (URIRef, Literal, BNode)):
            raise TypeError(f"Invalid type for value: {type(value)}")
        self.bindings[param] = value

    @property
    def parameters(self):
        return self.template.parameters

    def to_variadic(self, parameter: str):
        """
        Marks the given parameter as variadic. This means that
        the parameter can be bound to multiple values. After a parameter
        has been made variadic, we can refer to any {parameter}{i} parameter name
        where i is an integer starting from 0.

        Before:
        t = ctx['junction'](name='my_junc')
        t['in'] = pumpA['out']
        t['in'] = pumpB['out'] # this would overwrite the previous value

        After:
        t = ctx['junction'](name='my_junc')
        t = t.to_variadic('in')
        t['in'] = pumpA['out'] # this will create a new parameter 'in0'
        t['in'] = pumpB['out'] # this will create a new parameter 'in1'
        """
        if parameter not in self.template.parameters:
            raise KeyError(f"Invalid parameter: {parameter}")
        self.variadic_parameters.add(parameter)

    def _is_variadic(self, parameter: str) -> bool:
        """
        Checks if the given parameter is variadic. A variadic parameter
        can be bound to multiple values.

        :param parameter: The parameter to check
        :return: True if the parameter is variadic, False otherwise
        """
        return (
            parameter in self.variadic_parameters
            and parameter in self.template.parameters
        )

    def _has_variadic_values(self, parameter: str) -> bool:
        """
        Checks if the given parameter has any variadic values bound to it.
        This is used to determine if the parameter can be made variadic.

        :param parameter: The parameter to check
        :return: True if the parameter has variadic values, False otherwise
        """
        if not self._is_variadic(parameter):
            raise ValueError(f"Parameter {parameter} is not variadic")
        return any(name.startswith(parameter) for name in self.bindings)

    def _get_fresh_variadic(self, parameter: str) -> str:
        """
        returns the smallest parameter{i} that is not bound yet, where i is an integer
        and parameter is the name of the variadic parameter.

        :param parameter: The name of the variadic parameter
        :return: an unbound variadic parameter name, e.g. 'in0' or 'out3'
        """
        if not self._is_variadic(parameter):
            raise ValueError(f"Parameter {parameter} is not variadic")
        i = 0
        while True:
            name = f"{parameter}{i}"
            if name not in self.bindings:
                break
            i += 1
        # now find all tripels in self.template.body that have this parameter
        # and *duplicate* them with the new name
        for s, p, o in self.template.body:
            new_s, new_p, new_o = s, p, o
            if s == PARAM[parameter]:
                new_s = PARAM[name]
            if p == PARAM[parameter]:
                new_p = PARAM[name]
            if o == PARAM[parameter]:
                new_o = PARAM[name]
            self.template.body.add((new_s, new_p, new_o))
        return name

    def compile(self) -> Graph:
        """
        Compiles the template into a graph. If there are still parameters
        to be bound, then the template will be returned. Otherwise, the
        template will be filled and the resulting graph will be returned.

        :return: A graph containing the compiled template
        :rtype: Graph
        """
        tmp = self.template.evaluate(self.bindings)
        # if this is true, there are still parameters to be bound
        if isinstance(tmp, Template):
            # remove all variadic_parameters if they have any bindings.
            # do this by looping through all parameters in the template.
            # IF any are variadic, then remove all triplets that have the parameter in the subject, predicate or object
            for param in tmp.parameters:
                if self._is_variadic(param) and self._has_variadic_values(param):
                    remove_triples_with_param(tmp.body, param)
            bindings, graph = tmp.fill(self.ns, include_optional=False)
            self.bindings.update(bindings)
            return graph
        else:
            return tmp


def remove_triples_with_param(graph: Graph, param: str):
    """
    Removes all triples from the graph that have the given parameter
    in the subject, predicate or object.

    :param graph: The graph to remove triples from
    :param param: The parameter to remove
    """
    for s, p, o in list(graph):
        if s == PARAM[param] or p == PARAM[param] or o == PARAM[param]:
            graph.remove((s, p, o))
