import rdflib
from rdflib import RDF, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import BRICK, A


def test_create_model(clean_building_motif):
    model = Model.create(name="my_model")

    assert isinstance(model, Model)
    assert model.name == "my_model"
    assert isinstance(model.graph, rdflib.Graph)


def test_load_model(clean_building_motif):
    m = Model.create(name="my_model")
    m.graph.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))

    result = Model.load(m.id)
    assert result.id == m.id
    assert result.name == m.name
    assert isomorphic(result.graph, m.graph)


def test_validate_model(clean_building_motif):
    # load library
    lib = Library.load(ontology_graph="tests/unit/fixtures/shapes/shape1.ttl")
    assert lib is not None

    BLDG = Namespace("urn:building/")
    m = Model.create(name=BLDG)
    m.add_triples((BLDG["vav1"], A, BRICK.VAV))

    valid = m.validate([lib.get_shape_collection()])
    assert not valid

    m.add_triples((BLDG["vav1"], A, BRICK.VAV))
    m.add_triples((BLDG["vav1"], BRICK.hasPoint, BLDG["sensor"]))
    m.add_triples((BLDG["sensor"], A, BRICK.Temperature_Sensor))

    valid = m.validate([lib.get_shape_collection()])
    assert valid
