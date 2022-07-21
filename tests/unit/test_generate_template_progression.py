from typing import Dict

from rdflib import Namespace, URIRef

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model, Template
from buildingmotif.progressive_creation import progressive_plan


def test_generate_valid_progression(bm: BuildingMOTIF):
    BLDG = Namespace("urn:bldg#")
    model = Model.create(BLDG)
    brick = Library.load(
        ontology_graph="tests/unit/fixtures/Brick1.3rc1-equip-only.ttl"
    )
    templates = Library.load(directory="tests/unit/fixtures/progressive/templates")
    template_sequence = progressive_plan(
        templates.get_templates(), brick.get_shape_collection().graph
    )

    bindings: Dict[str, URIRef] = {}
    for templ in template_sequence:
        templ = templ.evaluate(bindings)
        if isinstance(templ, Template):
            new_bindings, graph = templ.fill(BLDG)
            bindings.update(new_bindings)
        else:
            graph = templ
        model.add_graph(graph)

    print(model.graph.serialize())

    # test that model contains what we expect
    q1 = """SELECT ?tstat ?temp ?sp WHERE {
        ?tstat a brick:Thermostat ;
            brick:hasPoint ?temp, ?sp .
        ?temp a brick:Temperature_Sensor .
        ?sp a brick:Temperature_Setpoint .
    }"""
    assert len(list(model.graph.query(q1))) == 1

    q2 = """SELECT ?tstat ?room WHERE {
        ?tstat a brick:Thermostat ;
            brick:hasLocation ?room .
        ?room a brick:Room .
    }"""
    assert len(list(model.graph.query(q2))) == 1

    q3 = """SELECT ?zone ?room WHERE {
        ?room a brick:Room ;
            brick:isPartOf ?zone .
        ?zone a brick:HVAC_Zone .
    }"""
    assert len(list(model.graph.query(q3))) == 1
