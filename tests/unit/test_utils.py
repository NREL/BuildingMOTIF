import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, ShapeCollection
from buildingmotif.namespaces import BRICK, SH, XSD, A
from buildingmotif.utils import (
    PARAM,
    _param_name,
    approximate_graph_hash,
    get_parameters,
    get_template_parts_from_shape,
    replace_nodes,
    rewrite_shape_graph,
    shacl_validate,
    skip_uri,
)

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
    assert len(deps) == 0
    assert (PARAM["name"], A, MODEL["shape1"]) in body

    shape_graph = Graph()
    shape_graph.parse(
        data=PREAMBLE
        + """
    :shape1 a owl:Class, sh:NodeShape ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:node brick:Temperature_Sensor ;
            sh:minCount 1 ;
        ] .
    """
    )

    body, deps = get_template_parts_from_shape(MODEL["shape1"], shape_graph)
    assert len(deps) == 1
    assert deps[0]["template"] == str(BRICK.Temperature_Sensor)
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

    g = Graph()
    g.parse(
        data=PREAMBLE
        + """
    :a :ab :ac .
    """
    )
    replace_nodes(
        g,
        {
            MODEL["a"]: MODEL["a1"],
        },
    )

    assert (MODEL["a1"], MODEL["ab"], MODEL["ac"]) in g
    assert len(list(g.triples((None, None, None)))) == 1


def test_get_parameters():
    body = Graph()
    body.parse(
        data="""
    @prefix P: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    P:name a brick:VAV ;
        brick:hasPoint P:1, P:2, P:3, P:4 .
    """
    )
    assert get_parameters(body) == {"name", "1", "2", "3", "4"}


def test_inline_sh_nodes(shacl_engine):
    shape_g = Graph()
    shape_g.parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix : <urn:ex/> .

    :shape1 a sh:NodeShape;
        sh:node :shape2, :shape3 .

    :shape2 a sh:NodeShape ;
        sh:property [
            sh:path :path1 ;
            sh:class :class1 ;
        ] ;
    .
    :shape3 a sh:NodeShape ;
        sh:class :class2 ;
        sh:property [
            sh:path :path1 ;
            sh:node :shape4 ;
        ] ;
    .

    :shape4 a sh:NodeShape ;
        sh:property [
            sh:path :path2 ;
            sh:minCount 1 ;
        ] ;
    .
    """
    )
    # should pass
    valid, _, report = shacl_validate(shape_g)
    assert valid, report

    shape1_cbd = shape_g.cbd(URIRef("urn:ex/shape1"))
    assert len(shape1_cbd) == 3

    shape_g = rewrite_shape_graph(shape_g)
    # should pass
    valid, _, report = shacl_validate(shape_g)
    assert valid, report

    shape1_cbd = shape_g.cbd(URIRef("urn:ex/shape1"))
    assert len(shape1_cbd) == 8


def test_inline_sh_and(bm: BuildingMOTIF, shacl_engine):
    bm.shacl_engine = shacl_engine
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

    new_sg = rewrite_shape_graph(sg)

    sc = ShapeCollection.create()
    sc.add_graph(new_sg)

    ctx = model.validate([sc])
    assert not ctx.valid

    if shacl_engine == "pyshacl":
        assert (
            "Value class is not in classes (brick:Class2, brick:Class3)"
            in ctx.report_string
            or "Value class is not in classes (brick:Class3, brick:Class2)"
            in ctx.report_string
            or "Value class is not in classes (<https://brickschema.org/schema/Brick#Class3>, <https://brickschema.org/schema/Brick#Class2>)"
            in ctx.report_string
            or "Value class is not in classes (<https://brickschema.org/schema/Brick#Class2>, <https://brickschema.org/schema/Brick#Class3>)"
            in ctx.report_string
        ), ctx.report_string
        assert (
            "Less than 1 values on <urn:model#x>->brick:relationship"
            in ctx.report_string
            or "Less than 1 values on <urn:model#x>-><https://brickschema.org/schema/Brick#relationship>"
            in ctx.report_string
        )
    elif shacl_engine == "topquadrant":
        assert (None, SH.resultPath, BRICK.relationship) in ctx.report
        assert (
            None,
            SH.resultMessage,
            Literal("Property needs to have at least 1 value"),
        ) in ctx.report

        assert (
            None,
            SH.resultMessage,
            Literal("Value must be an instance of brick:Class3"),
        ) in ctx.report
        assert (None, SH.sourceShape, URIRef("urn:model#shape1")) in ctx.report


def test_inline_sh_node(bm: BuildingMOTIF, shacl_engine):
    bm.shacl_engine = shacl_engine
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

    new_sg = rewrite_shape_graph(sg)

    sc = ShapeCollection.create()
    sc.add_graph(new_sg)

    ctx = model.validate([sc])
    assert not ctx.valid, ctx.report_string
    if shacl_engine == "pyshacl":
        assert (
            "Value class is not in classes (brick:Class2, brick:Class3)"
            in ctx.report_string
            or "Value class is not in classes (brick:Class3, brick:Class2)"
            in ctx.report_string
            or "Value class is not in classes (<https://brickschema.org/schema/Brick#Class3>, <https://brickschema.org/schema/Brick#Class2>)"
            in ctx.report_string
            or "Value class is not in classes (<https://brickschema.org/schema/Brick#Class2>, <https://brickschema.org/schema/Brick#Class3>)"
            in ctx.report_string
        )
        assert (
            "Less than 1 values on <urn:model#x>->brick:relationship"
            in ctx.report_string
            or "Less than 1 values on <urn:model#x>-><https://brickschema.org/schema/Brick#relationship>"
            in ctx.report_string
        )
    elif shacl_engine == "topquadrant":
        assert (None, SH.resultPath, BRICK.relationship) in ctx.report
        assert (
            None,
            SH.resultMessage,
            Literal("Property needs to have at least 1 value"),
        ) in ctx.report

        assert (
            None,
            SH.resultMessage,
            Literal("Value must be an instance of brick:Class3"),
        ) in ctx.report
        assert (None, SH.sourceShape, URIRef("urn:model#shape1")) in ctx.report


def test_param_name():
    good_p = PARAM["abc"]
    assert _param_name(good_p) == "abc"

    bad_p = BRICK["abc"]
    with pytest.raises(AssertionError):
        _param_name(bad_p)


def test_skip_uri():
    assert skip_uri(XSD.integer)
    assert skip_uri(SH.NodeShape)
    assert not skip_uri(BRICK.Sensor)


def test_hash(bm: BuildingMOTIF):
    graph = Graph()
    graph.parse("tests/unit/fixtures/smallOffice_brick.ttl")

    graph.add((MODEL["a"], A, BRICK["AHU"]))

    model = Model.create(MODEL)
    model.add_graph(graph)
    before_hash = approximate_graph_hash(model.graph)

    assert (
        approximate_graph_hash(graph) == before_hash
    ), "Graph did not change but hash did"

    triple_to_add = (MODEL["b"], A, BRICK["Sensor"])
    model.graph.add(triple_to_add)

    after_hash = approximate_graph_hash(model.graph)
    assert before_hash != after_hash, "Graph changed, but hashes did not"

    model.graph.remove(triple_to_add)

    after_hash = approximate_graph_hash(model.graph)
    assert before_hash == after_hash, "Graph with same state resulted in different hash"
