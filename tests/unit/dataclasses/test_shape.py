import rdflib
from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.dataclasses.shape_collection import ShapeCollection


def test_create_shape_collection(clean_building_motif):
    shape_collection = ShapeCollection.create()

    assert isinstance(shape_collection, ShapeCollection)
    assert isinstance(shape_collection.graph, rdflib.Graph)


def test_load_shape(clean_building_motif):
    shape_collection = ShapeCollection.create()
    shape_collection.graph.add(
        (URIRef("http://example.org/alex"), RDF.type, FOAF.Person)
    )

    result = ShapeCollection.load(shape_collection.id)
    assert result.id == shape_collection.id
    assert isomorphic(result.graph, shape_collection.graph)


def test_get_shapes_of_definition_type(clean_building_motif):
    shape_collection = ShapeCollection.create()
    shape_collection.graph.parse(
        data="""
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix : <urn:model#> .
    @prefix bmotif: <https://nrel.gov/BuildingMOTIF#> .

    :shape1 a owl:Class, sh:NodeShape ;
        bmotif:Definition_Type bmotif:System_Specification ;
    .

    :shape2 a owl:Class, sh:NodeShape ;
    .
    """
    )

    assert shape_collection.get_shapes_of_definition_type(
        URIRef("https://nrel.gov/BuildingMOTIF#System_Specification")
    ) == [URIRef("urn:model#shape1")]


def test_get_shapes_of_domain(clean_building_motif):
    shape_collection = ShapeCollection.create()
    shape_collection.graph.parse(
        data="""
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix : <urn:model#> .
    @prefix bmotif: <https://nrel.gov/BuildingMOTIF#> .

    :shape1 a bmotif:HVAC ;
    .

    :shape2 a owl:Class, sh:NodeShape ;
    .
    """
    )

    assert shape_collection.get_shapes_of_domain(
        URIRef("https://nrel.gov/BuildingMOTIF#HVAC")
    ) == [URIRef("urn:model#shape1")]
