import pytest
from rdflib import URIRef

from buildingmotif.dataclasses import Library, Model
from buildingmotif.dataclasses.compiled_model import CompiledModel


def test_compiled_model_validation(clean_building_motif_topquadrant):
    model = Model.from_file("tests/unit/fixtures/compilation/brick_model.ttl")
    brick = Library.load(
        ontology_graph="tests/unit/fixtures/Brick.ttl"
    ).get_shape_collection()
    shape_collection = Library.load(
        ontology_graph="tests/unit/fixtures/compilation/shapes.ttl"
    ).get_shape_collection()
    compiled_model = model.compile([shape_collection, brick])

    assert isinstance(
        compiled_model, CompiledModel
    ), "Compiled model is not an instance of CompiledModel"
    assert compiled_model.model, "Model is not set in CompiledModel"

    validation_context = compiled_model.validate()
    assert validation_context is not None
    assert not validation_context.valid


def test_compiled_model_compilation(clean_building_motif_topquadrant):
    model = Model.from_file("tests/unit/fixtures/compilation/s223_model.ttl")
    s223 = Library.load(
        ontology_graph="libraries/ashrae/223p/ontology/223p.ttl"
    ).get_shape_collection()
    compiled_model = model.compile([s223])

    # check that pt1:DumbSwitch has a connectedTo relationship to pt2:Luminaire
    res = compiled_model.graph.query(
        """ASK {
        <http://data.ashrae.org/standard223/1.0/data/patterns-scenario3#ElectricBreaker_1> <http://data.ashrae.org/standard223#connectedTo> <http://data.ashrae.org/standard223/1.0/data/patterns-scenario3#Luminaire> .
    }"""
    )
    compiled_model.graph.serialize("/tmp/compiled_model.ttl", format="turtle")
    assert bool(
        res
    ), "DumbSwitch is not connectedTo Luminaire, so s223 inference did not run to completion"


def test_compiled_model_shape_to_df(clean_building_motif_topquadrant):
    model = Model.from_file("tests/unit/fixtures/compilation/brick_model.ttl")
    shape_collection = Library.load(
        ontology_graph="tests/unit/fixtures/compilation/shapes.ttl"
    ).get_shape_collection()
    compiled_model = model.compile([shape_collection])

    with pytest.raises(ValueError):
        shape_uri = URIRef("urn:shape1/does_not_exist")
        compiled_model.shape_to_df(shape_uri)

    shape_uri = URIRef("urn:shape1/vav_shape")
    df = compiled_model.shape_to_df(shape_uri)
    assert df is not None
    print(df.columns)
    assert set(df.columns) == {"target", "hasAirFlowSensor"}
