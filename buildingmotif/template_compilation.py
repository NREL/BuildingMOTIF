from typing import Callable, Dict

import rdflib

from buildingmotif.namespaces import BRICK, PARAM, RDF
from buildingmotif.utils import new_temporary_graph

RULES: Dict[str, Callable] = {}

"""
Notes:
- maybe more useful for authoring than for distribution
- "compile" into template definitions which then get distributed
- standardize the "subject" of the template: 'name' param
- have rules generate dependencies rather than introducing additional subjects?
- give the rules/macros access to the template library and/or the template they
  are associated with?:
    - new signature: def foo(library, template, *args, **kwargs) -> rdflib.Graph
- don't hardcode template names into these rules/macros --- pass in from user
"""

# TODO: can i write a rule that mandates all Points have a BACnet reference?


def rule(name: str):
    """
    This decorator is applied to a function in order to register that function
    as a rule which can be executed during template compilation.
    """

    def wrapper(func: Callable):
        RULES[name] = func
        return func

    return wrapper


@rule("body")
def body(*args, **kwargs) -> rdflib.Graph:
    """
    Returns the first value of the 'body' argument as the template body
    """
    G = new_temporary_graph()
    G.parse(data=args[0], format="turtle")
    return G


@rule("type")
def hasType(*args, **kwargs) -> rdflib.Graph:
    """
    Returns the first value of the 'body' argument as the template body
    """
    G = new_temporary_graph()
    for arg in args:
        arg = rdflib.URIRef(arg)
        G.add((PARAM["name"], RDF["type"], arg))
    return G


@rule("hasPoint")
def points(*args, **kwargs) -> rdflib.Graph:
    G = new_temporary_graph()
    for param, pointtype in kwargs.items():
        pointtype = rdflib.URIRef(pointtype)
        G.add(
            (PARAM[param], RDF["type"], pointtype)
        )  # should really be a dependency on that type
        G.add((PARAM["name"], BRICK.hasPoint, PARAM[param]))
    return G


@rule("hasPart")
def parts(*args, **kwargs) -> rdflib.Graph:
    G = new_temporary_graph()
    for param, pointtype in kwargs.items():
        pointtype = rdflib.URIRef(pointtype)
        G.add(
            (PARAM[param], RDF["type"], pointtype)
        )  # should really be a dependency on that type
        G.add((PARAM["name"], BRICK.hasPart, PARAM[param]))
    return G


@rule("upstream")
def isFedBy(*args, **kwargs) -> rdflib.Graph:
    G = new_temporary_graph()
    assert kwargs is not None
    for param, equiptype in kwargs.items():
        equiptype = rdflib.URIRef(equiptype)
        G.add((PARAM[param], RDF["type"], equiptype))
        G.add((PARAM["name"], BRICK.isFedBy, PARAM[param]))
    return G


@rule("downstream")
def feeds(*args, **kwargs) -> rdflib.Graph:
    G = new_temporary_graph()
    assert kwargs is not None
    for param, equiptype in kwargs.items():
        equiptype = rdflib.URIRef(equiptype)
        G.add((PARAM[param], RDF["type"], equiptype))
        G.add((PARAM["name"], BRICK.feeds, PARAM[param]))
    return G


def compile_template_spec(spec: Dict) -> Dict:
    """
    Compiles a template specification into the body of a template by
    applying rules defined in this file and others

    :param spec: the Python dictionary that is the result of decoding the
        YAML structure (usually a dictionary or list) defining the
        template
    :type spec: Dict
    :return: the template spec containing the compiled body
    :rtype: Dict
    """
    # extract metadata that doesn't correspond to rule executions
    head = spec.pop("head", [])
    deps = spec.pop("dependencies", [])
    optionals = spec.pop("optional", [])

    # compile the template's bo from the rules
    body = new_temporary_graph()
    for rule_name in tuple(spec.keys()):
        rule_args = spec.pop(rule_name)
        if rule_name not in RULES:
            raise ValueError(f"Unknown rule {rule_name}")
        if isinstance(rule_args, dict):
            G = RULES[rule_name](**rule_args)
        elif isinstance(rule_args, list):
            G = RULES[rule_name](*rule_args)
        else:
            G = RULES[rule_name](*[rule_args])
        body += G

    # put the metadata back
    spec["head"] = head
    spec["dependencies"] = deps
    spec["body"] = body
    spec["optional"] = optionals
    return spec
