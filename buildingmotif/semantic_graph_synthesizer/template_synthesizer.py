import os
from collections import deque
from functools import lru_cache
from typing import List, Optional, Tuple

import yaml
from rdflib import Graph, URIRef

from buildingmotif.dataclasses import Library, Template
from buildingmotif.namespaces import PARAM, RDF, bind_prefixes
from buildingmotif.semantic_graph_synthesizer.classes import Token, TokenizedLabel


class _GeneratedTemplate:
    """
    Graph contains the template body with its parameters. last_type and last_param are the last type and parameter added to the template
    """

    graph: Graph
    last_type: URIRef
    params: List[URIRef]

    def __init__(self, classname: URIRef, param: URIRef = PARAM["name"]):
        self.graph = Graph()
        bind_prefixes(self.graph)
        self.params = []
        self.add_type(classname, param)

    @property
    def last_param(self):
        return self.params[-1]

    @property
    def size(self):
        return len(self.params)

    def add_type(self, classname: URIRef, param: URIRef, pred: Optional[URIRef] = None):
        self.graph.add((param, RDF.type, classname))
        if pred:
            self.graph.add((self.last_param, pred, param))
        self.last_type = classname
        self.params.append(param)

    def copy(self):
        t = _GeneratedTemplate(self.last_type, self.last_param)
        t.graph += self.graph
        t.params = self.params[:]
        return t


class BrickTemplateSynthesizer:
    def __init__(self, brick_ontology: Library, dest_library: Library):
        """
        Creates templates for the Brick ontology and puts them in the destination library
        """
        self.ontology: Graph = brick_ontology.get_shape_collection().graph
        self.library: Library = dest_library
        self._i = 0

    def _gensym(self) -> URIRef:
        self._i += 1
        return PARAM[f"p{self._i}"]

    def _generate_links(
        self, templ: _GeneratedTemplate, root: URIRef, param: URIRef
    ) -> List[_GeneratedTemplate]:
        """
        Given a root class, generate all possible links which start from the root class
        """
        for prop in self.class_predicates(root):
            for class_ in self.class_predicate_classes(root, prop):
                g = templ.copy()
                g.add_type(class_, self._gensym(), prop)
                yield g

    def generate_graphs(
        self, classname: URIRef, size: int = 5
    ) -> List[_GeneratedTemplate]:
        t1 = _GeneratedTemplate(classname)
        templates = deque([t1])
        finished = []
        while templates:
            t = templates.popleft()
            if t.size >= size:
                _, _, value = t.graph.compute_qname(classname)
                generated_template = self.library.create_template(
                    f"autogen_template_{value}_{len(finished)}", t.graph
                )
                finished.append(generated_template)
                continue
            for p in t.params:
                for g in self._generate_links(t, t.last_type, p):
                    print(g.params)
                    print(g.graph.serialize(format="turtle"))
                    templates.append(g)
        return list(finished)

    def write_templates(self, templates: List[Template]):
        # serialize the templates to a .yml file
        os.makedirs("templates", exist_ok=True)
        dicts = {t.name: {"body": t.body.serialize(format="turtle")} for t in templates}
        yaml.dump(dicts, open("templates/templates.yml", "w"))

    def get_templates(self, classname: URIRef, size: int = 5) -> List[Template]:
        """
        Given a class name, generate templates for the class
        """
        i = 0

        def _gensym() -> URIRef:
            nonlocal i
            i += 1
            return PARAM[f"p{i}"]

        t1 = _GeneratedTemplate(classname)
        templates = deque([t1])
        template_bodies = []

        # Generates templates with 'size' number of parameters for the given class:
        # 1. get all properties for this class
        # 2. for each property, get the class that it points to
        # 3. generate a template for each pair of (property, class)
        # 4. add the template to the list of templates
        # TODO: these templates are "chain" rather than "bushy" - we need to generate more templates,
        # i.e. by connecting multiple properties to the 'name' parameter
        while templates:
            t = templates.popleft()
            print(t, t.params, size)
            print(t.graph.serialize(format="turtle"))
            if len(set(t.params)) >= size:
                template_bodies.append(t)
                continue
            # get all properties for this class
            props = self.class_predicates(t.last_type)
            for prop in props:
                # get the classes that the property can point to
                classes = self.class_predicate_classes(t.last_type, prop)
                for c in classes:
                    print(f"Adding {c} to {prop} on {t.last_type}")
                    t2 = t.copy()
                    p = _gensym()
                    t2.add_type(c, p, prop)
                    templates.append(t2)

        # create the templates in the library
        finished: List[Template] = []
        for i, template_body in enumerate(template_bodies):
            # breaks up "https://brickschema.org/schema/Brick#AHU" into "brick:", "https://brickschema.org/schema/Brick#", "AHU"
            _, _, value = template_body.graph.compute_qname(classname)
            generated_template = self.library.create_template(
                f"autogen_template_{value}_{i}", template_body.graph
            )
            finished.append(generated_template)

        # serialize the templates to a .yml file
        os.makedirs("templates", exist_ok=True)
        dicts = [
            {t.name: {"body": t.body.serialize(format="turtle")}} for t in finished
        ]
        yaml.dump(dicts, open("templates/templates.yml", "w"))

        return finished

    def get_root_class(self, classname: URIRef) -> URIRef:
        """
        Given a class, it returns the root class. One of: Brick.Point, Brick.Equipment, Brick.Location
        """
        query = """SELECT ?root_class WHERE {
            { ?class brick:aliasOf?/rdfs:subClassOf* brick:Point . BIND(brick:Point as ?root_class) }
            UNION
            { ?class brick:aliasOf?/rdfs:subClassOf* brick:Equipment . BIND(brick:Equipment as ?root_class) }
            UNION
            { ?class brick:aliasOf?/rdfs:subClassOf* brick:Location . BIND(brick:Location as ?root_class) }
        }"""
        res = list(self.ontology.query(query, initBindings={"class": classname}))
        return res[0][0]

    @lru_cache(maxsize=20)
    def class_predicate_class(self, fromc: URIRef, to: URIRef) -> List[URIRef]:
        """
        Given a class, it returns the possible relationships from SHACL NodeShapes and PropertyShapes
        """

        # 1. get a parent class of 'from' which is a targetClass of a Node Shape. Get all sh:property/sh:path values on that NodeShape
        query = """SELECT ?path WHERE {
            ?from brick:aliasOf?/rdfs:subClassOf* ?fromp .
            ?to brick:aliasOf?/rdfs:subClassOf* ?top .
            { ?shape sh:targetClass ?fromp }
            UNION
            { ?fromp a sh:NodeShape . BIND(?fromp as ?shape) }
            ?shape sh:property ?prop .
            ?prop sh:path ?path .
            { ?prop sh:class ?top }
            UNION
            { ?prop sh:or/rdf:rest*/rdf:first ?top }
        }"""
        res = list(
            self.ontology.query(query, initBindings={"from": fromc, "to": to}).bindings
        )
        paths = set([r["path"] for r in res])
        return paths

    @lru_cache(maxsize=20)
    def class_predicate_classes(self, fromc: URIRef, pred: URIRef) -> List[URIRef]:
        """
        Given a class and a predicate, it returns the possible classes that the predicate can point to
        """
        query = """SELECT ?to WHERE {
            ?from brick:aliasOf?/rdfs:subClassOf* ?fromp .
            ?fromp a sh:NodeShape .
            ?fromp sh:property ?prop .
            ?prop sh:path ?pred .
            ?prop sh:class ?to .
            { ?to rdfs:subClassOf* brick:Equipment }
            UNION
            { ?to rdfs:subClassOf* brick:Location }
            UNION
            { ?to rdfs:subClassOf* brick:Point }
        }"""
        res = list(
            self.ontology.query(
                query, initBindings={"from": fromc, "pred": pred}
            ).bindings
        )
        tos = set([r["to"] for r in res])
        return tos

    def predicates(self) -> List[URIRef]:
        """
        Returns all possible relationships between two classes
        """
        query = """SELECT ?path WHERE {
            {
            ?shape sh:property ?prop .
            ?prop sh:path ?path .
            }
            UNION
            {
            ?path a owl:ObjectProperty .
            }
        }"""
        res = list(self.ontology.query(query).bindings)
        paths = set([r["path"] for r in res])
        return paths

    @lru_cache(maxsize=20)
    def class_predicates(self, fromc: URIRef) -> List[URIRef]:
        """
        Given a class, it returns the possible relationships from the class
        """

        # 1. get a parent class of 'from' which is a targetClass of a Node Shape. Get all sh:property/sh:path values on that NodeShape
        query = """SELECT ?path WHERE {
            ?from brick:aliasOf?/rdfs:subClassOf* ?fromp .
            { ?shape sh:targetClass ?fromp }
            UNION
            { ?fromp a sh:NodeShape . BIND(?fromp as ?shape) }
            ?shape sh:property ?prop .
            ?prop sh:path ?path .
            FILTER NOT EXISTS { ?path a brick:EntityProperty }
        }"""
        res = list(self.ontology.query(query, initBindings={"from": fromc}).bindings)
        paths = set([r["path"] for r in res])
        return paths
