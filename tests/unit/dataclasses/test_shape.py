import rdflib
from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.dataclasses.shape import Shape


def test_create_shape(clean_building_motif):
    shape = Shape.create()

    assert isinstance(shape, Shape)
    assert isinstance(shape.graph, rdflib.Graph)


def test_load_shape(clean_building_motif):
    shape = Shape.create()
    shape.graph.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))

    result = Shape.load(shape.id)
    assert result.id == shape.id
    assert isomorphic(result.graph, shape.graph)
