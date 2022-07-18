from rdflib import Graph, Literal, Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import RDFS

BLDG = Namespace("urn:building/")


def test_model_validate(bm: BuildingMOTIF):
    """
    Test that a model correctly validates
    """
    shape_graph_data = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix : <urn:shape_graph/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
: a owl:Ontology .
:zone_shape a sh:NodeShape ;
    sh:targetClass brick:HVAC_Zone ;
    sh:message "all HVAC zones must have a label" ;
    sh:property [
        sh:path rdfs:label ;
        sh:minCount 1 ;
    ] .
    """
    shape_graph = Graph().parse(data=shape_graph_data)
    shape_lib = Library.load(ontology_graph=shape_graph)

    lib = Library.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"name", "cav"}

    # create model from template
    model = Model.create(BLDG)
    bindings, hvac_zone_instance = zone.fill(BLDG)
    model.add_graph(hvac_zone_instance)

    # validate the graph (should fail because there are no labels)
    valid, report_g, report_txt = model.validate([shape_lib.get_shape_collection()])
    assert isinstance(report_g, Graph)
    assert isinstance(report_txt, str)
    assert isinstance(valid, bool)
    assert not valid

    model.add_triples((bindings["name"], RDFS.label, Literal("hvac zone 1")))
    # validate the graph (should now be valid)
    valid, report_g, report_txt = model.validate([shape_lib.get_shape_collection()])
    assert isinstance(report_g, Graph)
    assert isinstance(report_txt, str)
    assert isinstance(valid, bool)
    assert valid
