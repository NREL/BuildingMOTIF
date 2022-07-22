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

    :shape1 a owl:Class, bmotif:Definition_Type ;
    .

    :shape2 a owl:Class, bmotif:Sequence_Of_Operations ;
    .

    :shape3 a owl:Class, bmotif:Analytics_Application ;
    .
    """
    )

    assert shape_collection.get_shapes_of_definition_type(
        URIRef("https://nrel.gov/BuildingMOTIF#Definition_Type")
    ) == [
        URIRef("urn:model#shape1"),
        URIRef("urn:model#shape2"),
        URIRef("urn:model#shape3"),
    ]

    assert shape_collection.get_shapes_of_definition_type(
        URIRef("https://nrel.gov/BuildingMOTIF#Sequence_Of_Operations")
    ) == [URIRef("urn:model#shape2")]

    assert shape_collection.get_shapes_of_definition_type(
        URIRef("https://nrel.gov/BuildingMOTIF#Analytics_Application")
    ) == [URIRef("urn:model#shape3")]


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

    :shape2 a bmotif:Lighting ;
    .

    :shape3 a bmotif:Electrical ;
    .
    """
    )

    assert shape_collection.get_shapes_of_domain(
        URIRef("https://nrel.gov/BuildingMOTIF#HVAC")
    ) == [URIRef("urn:model#shape1")]

    assert shape_collection.get_shapes_of_domain(
        URIRef("https://nrel.gov/BuildingMOTIF#Lighting")
    ) == [URIRef("urn:model#shape2")]

    assert shape_collection.get_shapes_of_domain(
        URIRef("https://nrel.gov/BuildingMOTIF#Electrical")
    ) == [URIRef("urn:model#shape3"), URIRef("urn:model#shape2")]
