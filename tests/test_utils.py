from rdflib import Graph, Namespace

from buildingmotif.namespaces import BRICK, A
from buildingmotif.utils import PARAM, get_template_parts_from_shape, replace_nodes

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
@prefix : <urn:model#> .
"""
MODEL = Namespace("urn:model#")


def test_get_template_parts_from_shape():
    shape_graph = Graph()
    shape_graph.parse(
        data=PREAMBLE
        + """
    :shape1 a owl:Class, sh:NodeShape ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:class brick:Temperature_Sensor ;
            sh:minCount 1 ;
        ] .
    """
    )
    body, deps = get_template_parts_from_shape(MODEL["shape1"], shape_graph)
    assert len(deps) == 1
    assert deps[0]["rule"] == BRICK.Temperature_Sensor
    assert list(deps[0]["args"].keys()) == ["name"]
    assert (PARAM["name"], A, MODEL["shape1"]) in body
    # assert (PARAM['name'], BRICK.hasPoint,


def test_replace_nodes():
    g = Graph()
    g.parse(
        data=PREAMBLE
        + """
    :a :b :c .
    :d :e :f .
    """
    )
    replace_nodes(
        g,
        {
            MODEL["a"]: MODEL["a1"],
            MODEL["b"]: MODEL["b1"],
            MODEL["f"]: MODEL["f1"],
        },
    )

    assert (MODEL["a1"], MODEL["b1"], MODEL["c"]) in g
    assert (MODEL["d"], MODEL["e"], MODEL["f1"]) in g
    assert len(list(g.triples((None, None, None)))) == 2
