import rdflib
from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from building_motif.dataclasses.model import Model


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
