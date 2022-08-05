import rdflib
from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.dataclasses.library import Library
from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.namespaces import BMOTIF, BRICK


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

    assert set(
        shape_collection.get_shapes_of_definition_type(BMOTIF.Definition_Type)
    ) == {
        URIRef("urn:model#shape1"),
        URIRef("urn:model#shape2"),
        URIRef("urn:model#shape3"),
    }

    assert shape_collection.get_shapes_of_definition_type(
        BMOTIF.Sequence_Of_Operations
    ) == [URIRef("urn:model#shape2")]

    assert shape_collection.get_shapes_of_definition_type(
        BMOTIF.Analytics_Application
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

    assert shape_collection.get_shapes_of_domain(BMOTIF.HVAC) == [
        URIRef("urn:model#shape1")
    ]

    assert shape_collection.get_shapes_of_domain(BMOTIF.Lighting) == [
        URIRef("urn:model#shape2")
    ]

    assert set(shape_collection.get_shapes_of_domain(BMOTIF.Electrical)) == {
        URIRef("urn:model#shape3"),
        URIRef("urn:model#shape2"),
    }


def test_shape_collection_resolve_imports(clean_building_motif):
    Library.load(ontology_graph="tests/unit/fixtures/Brick1.3rc1-equip-only.ttl")
    Library.load(ontology_graph="buildingmotif/resources/constraints.ttl")
    lib = Library.load(ontology_graph="tests/unit/fixtures/shapes/import_test.ttl")
    sc = lib.get_shape_collection()
    new_sc = sc.resolve_imports()
    assert new_sc is not None
    assert len(new_sc.graph) > len(sc.graph)


def test_get_shapes_for_class(clean_building_motif):
    brick = Library.load(
        ontology_graph="tests/unit/fixtures/Brick1.3rc1-equip-only.ttl"
    )
    lib = Library.load(ontology_graph="tests/unit/fixtures/shapes/shape1.ttl")
    sc = lib.get_shape_collection()
    shapes = sc.get_shapes_about_class(BRICK["VAV"], [brick.get_shape_collection()])
    assert len(shapes) == 2
    shapes = sc.get_shapes_about_class(
        BRICK["Terminal_Unit"], [brick.get_shape_collection()]
    )
    assert len(shapes) == 1
