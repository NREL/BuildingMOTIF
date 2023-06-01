from rdflib import Graph, Namespace
from rdflib.compare import isomorphic

from buildingmotif.dataclasses import Library, Model, ShapeCollection
from buildingmotif.namespaces import PARAM, SH


def test_template_to_shape_simple(bm):
    lib = Library.load(directory="tests/unit/fixtures/templates")

    sup_fan_templ = lib.get_template_by_name("supply-fan")
    shape = sup_fan_templ.to_nodeshape()
    assert isinstance(shape, Graph), "Returned shape should be a graph"
    expected_graph_ttl = """
    @prefix p: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    p:supply-fan a sh:NodeShape ;
        sh:class brick:Supply_Fan ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:qualifiedValueShape [ sh:class brick:Fan_Speed_Command ] ;
            sh:qualifiedMinCount 1 ;
        ] ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:qualifiedValueShape [ sh:class brick:Fan_Status ] ;
            sh:qualifiedMinCount 1 ;
        ] ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:qualifiedValueShape [ sh:class brick:Start_Stop_Command ] ;
            sh:qualifiedMinCount 1 ;
        ] ;
    .
    """
    expected_graph = Graph()
    expected_graph.parse(data=expected_graph_ttl, format="ttl")
    assert isomorphic(
        shape, expected_graph
    ), f"Graphs were not isomorphic! Expected:\n{expected_graph.serialize()}\nActual:\n{shape.serialize()}"


def test_template_to_shape_optional(bm):
    lib = Library.load(directory="tests/unit/fixtures/templates")

    oad_templ = lib.get_template_by_name("outside-air-damper")
    shape = oad_templ.to_nodeshape()
    assert isinstance(shape, Graph), "Returned shape should be a graph"
    expected_graph_ttl = """
    @prefix p: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    p:outside-air-damper a sh:NodeShape ;
        sh:class brick:Outside_Air_Damper ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:qualifiedValueShape [ sh:class brick:Damper_Position_Command ] ;
            sh:qualifiedMinCount 1 ;
        ] ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:qualifiedValueShape [ sh:class brick:Damper_Position_Sensor] ;
            sh:qualifiedMinCount 0 ;
        ] ;
    .
    """
    expected_graph = Graph()
    expected_graph.parse(data=expected_graph_ttl, format="ttl")
    assert isomorphic(
        shape, expected_graph
    ), f"Graphs were not isomorphic! Expected:\n{expected_graph.serialize()}\nActual:\n{shape.serialize()}"


def test_template_to_shape_dependency(bm):
    lib = Library.load(directory="tests/unit/fixtures/templates")

    vav_templ = lib.get_template_by_name("vav")
    shape = vav_templ.to_nodeshape()
    assert isinstance(shape, Graph), "Returned shape should be a graph"
    expected_graph_ttl = """
    @prefix p: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    p:vav a sh:NodeShape ;
        sh:class brick:VAV ;
        sh:property [
            sh:path brick:feeds ;
            sh:minCount 1 ;
        ] ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:node p:temp-sensor ;
            sh:minCount 1 ;
        ] ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:minCount 1 ;
        ] ;
    .
    p:temp-sensor a sh:NodeShape ;
        sh:class brick:Temperature_Sensor .
    """
    expected_graph = Graph()
    expected_graph.parse(data=expected_graph_ttl, format="ttl")
    assert isomorphic(
        shape, expected_graph
    ), f"Graphs were not isomorphic! Expected:\n{expected_graph.serialize()}\nActual:\n{shape.serialize()}"


def test_template_to_shape_duplicate_props_with_optional(bm):
    lib = Library.create("temp_lib")
    t = lib.create_template("temp_template")
    t.body.parse(
        data="""
    @prefix P: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    P:name a brick:VAV ;
        brick:hasPoint P:1, P:2 .
    P:1 a brick:Temperature_Sensor .
    P:2 a brick:Temperature_Sensor .
    """,
        format="ttl",
    )
    t.optional_args.append("1")

    shape = t.to_nodeshape()
    assert isinstance(shape, Graph), "Returned shape should be a graph"
    expected_graph_ttl = """
    @prefix p: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    p:temp_template a sh:NodeShape ;
        sh:class brick:VAV ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:class brick:Temperature_Sensor ;
            sh:minCount 1 ;
        ] ;
    .
    """
    expected_graph = Graph()
    expected_graph.parse(data=expected_graph_ttl, format="ttl")
    assert isomorphic(
        shape, expected_graph
    ), f"Graphs were not isomorphic! Expected:\n{expected_graph.serialize()}\nActual:\n{shape.serialize()}"


def test_template_to_shape_duplicate_props(bm):
    lib = Library.create("temp_lib")
    t = lib.create_template("temp_template")
    t.body.parse(
        data="""
    @prefix P: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    P:name a brick:VAV ;
        brick:hasPoint P:1, P:2 .
    P:1 a brick:Temperature_Sensor .
    P:2 a brick:Temperature_Sensor .
    """,
        format="ttl",
    )

    shape = t.to_nodeshape()
    assert isinstance(shape, Graph), "Returned shape should be a graph"
    expected_graph_ttl = """
    @prefix p: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    p:temp_template a sh:NodeShape ;
        sh:class brick:VAV ;
        sh:property [
            sh:path brick:hasPoint ;
            sh:class brick:Temperature_Sensor ;
            sh:minCount 2 ;
        ] ;
    .
    """
    expected_graph = Graph()
    expected_graph.parse(data=expected_graph_ttl, format="ttl")
    assert isomorphic(
        shape, expected_graph
    ), f"Graphs were not isomorphic! Expected:\n{expected_graph.serialize()}\nActual:\n{shape.serialize()}"


def test_template_to_shape_validates(bm, library):
    BLDG = Namespace("urn:bldg/")
    model = Model.create(BLDG)
    lib = Library.load(ontology_graph="libraries/brick/Brick.ttl")
    lib = Library.load(directory=library)
    for template in lib.get_templates():
        # add the generated shape to our collection
        shape_collection = ShapeCollection.create()
        shape = template.to_nodeshape()
        shape_collection.add_graph(shape)

        # create an 'instance' graph from the template and add
        # it to the model
        bindings, instance = template.inline_dependencies().fill(
            BLDG, include_optional=True
        )
        instance_name = bindings["name"]
        # target the new node with the generated shape
        shape_collection.add_triples(
            (PARAM[template.name], SH.targetNode, instance_name)
        )
        # truncate model and re-populate
        model.graph.remove((None, None, None))
        model.add_graph(instance)

        report = model.validate([shape_collection])
        assert (
            report.valid
        ), f"Graph:\n{model.graph.serialize()}\n shape \n{shape.serialize()}\n failed to validate filled template {template.name}: {report.report_string}"
