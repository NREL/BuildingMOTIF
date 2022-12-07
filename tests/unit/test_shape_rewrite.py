from rdflib import Graph, Namespace

import buildingmotif.shape_rewrite as sw
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, ShapeCollection

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


def test_inline_sh_and(bm: BuildingMOTIF):
    sg = Graph()
    sg.parse(
        data=PREAMBLE
        + """
    :shape1 a sh:NodeShape, owl:Class ;
        sh:and ( :shape2 :shape3 :shape4 ) .
    :shape2 a sh:NodeShape ;
        sh:class brick:Class2 .
    :shape3 a sh:NodeShape ;
        sh:class brick:Class3 .
    :shape4 a sh:NodeShape ;
        sh:property [
            sh:path brick:relationship ;
            sh:class brick:Class4 ;
            sh:minCount 1 ;
        ] .
    """
    )

    data = Graph()
    data.parse(
        data=PREAMBLE
        + """
    :x a :shape1, brick:Class2 .
    """
    )
    model = Model.create(MODEL)
    model.add_graph(data)

    new_sg = sw.rewrite_shape_graph(sg)

    sc = ShapeCollection.create()
    sc.add_graph(new_sg)

    ctx = model.validate([sc])
    assert not ctx.valid
    assert (
        "Value class is not in classes (brick:Class2, brick:Class3)"
        in ctx.report_string
        or "Value class is not in classes (brick:Class3, brick:Class2)"
        in ctx.report_string
    ), ctx.report_string
    assert (
        "Less than 1 values on <urn:model#x>->brick:relationship" in ctx.report_string
    )


def test_inline_sh_node(bm: BuildingMOTIF):
    sg = Graph()
    sg.parse(
        data=PREAMBLE
        + """
    :shape1 a sh:NodeShape, owl:Class ;
        sh:node :shape2, :shape3, :shape4 .
    :shape2 a sh:NodeShape ;
        sh:class brick:Class2 .
    :shape3 a sh:NodeShape ;
        sh:class brick:Class3 .
    :shape4 a sh:NodeShape ;
        sh:property [
            sh:path brick:relationship ;
            sh:class brick:Class4 ;
            sh:minCount 1 ;
        ] .
    """
    )

    data = Graph()
    data.parse(
        data=PREAMBLE
        + """
    :x a :shape1, brick:Class2 .
    """
    )
    model = Model.create(MODEL)
    model.add_graph(data)

    new_sg = sw.rewrite_shape_graph(sg)

    sc = ShapeCollection.create()
    sc.add_graph(new_sg)

    ctx = model.validate([sc])
    assert not ctx.valid
    assert (
        "Value class is not in classes (brick:Class2, brick:Class3)"
        in ctx.report_string
        or "Value class is not in classes (brick:Class3, brick:Class2)"
        in ctx.report_string
    )
    assert (
        "Less than 1 values on <urn:model#x>->brick:relationship" in ctx.report_string
    )
