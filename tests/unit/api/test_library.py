from urllib.parse import quote
from unittest.mock import MagicMock, patch
from rdflib import URIRef

from buildingmotif.dataclasses import Library


def test_get_all_libraries(client, building_motif):
    # Setup
    Library.create("my_library")
    Library.create("your_library")

    # Act
    results = client.get("/libraries")

    # Assert
    assert results.status_code == 200

    db_libraries = building_motif.table_connection.get_all_db_libraries()
    assert results.json == [
        {
            "id": library.id,
            "name": library.name,
            "template_ids": [t.id for t in library.templates],
            "shape_collection_id": library.shape_collection_id,
        }
        for library in db_libraries
    ]


def test_get_all_shapes(client, building_motif):
    my_library = Library.create("my_library")
    shape_collection = my_library.get_shape_collection()
    shape_collection.graph.parse(
        data="""
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix : <urn:model#> .
    @prefix bmotif: <https://nrel.gov/BuildingMOTIF#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    :shape1 a owl:Class, bmotif:Definition_Type ;
        rdfs:label "a";
    .

    :shape2 a owl:Class, bmotif:Sequence_Of_Operations ;
        rdfs:label "b";
    .

    :shape3 a owl:Class, bmotif:Analytics_Application ;
        rdfs:label "c";
    .
    """
    )

    # Act
    results = client.get("/libraries/shapes")

    assert results.json == {
        "https://nrel.gov/BuildingMOTIF#Analytics_Application": [
            {
                "shape_uri": "urn:model#shape3",
                "library_name": "my_library",
                "shape_collection_id": shape_collection.id,
                "label": "c",
            },
        ],
        "https://nrel.gov/BuildingMOTIF#Sequence_Of_Operations": [
            {
                "shape_uri": "urn:model#shape2",
                "library_name": "my_library",
                "shape_collection_id": shape_collection.id,
                "label": "b",
            },
        ],
        "https://nrel.gov/BuildingMOTIF#System_Specification": [],
    }


def test_get_library(client, building_motif):
    # Setup
    lib = Library.create("my_library")
    lib.create_template("my_template")

    # Act
    results = client.get(f"/libraries/{lib.id}")

    # Assert
    assert results.status_code == 200

    db_library = building_motif.table_connection.get_db_library(lib.id)
    assert results.json == {
        "id": db_library.id,
        "name": db_library.name,
        "template_ids": [t.id for t in db_library.templates],
        "shape_collection_id": db_library.shape_collection_id,
    }


def test_get_library_not_found(client):
    # Act
    results = client.get("/libraries/-1")

    # Assert
    assert results.status_code == 404
    assert results.json == {"message": "ID: -1"}


def test_get_library_classes(client, building_motif):
    # Setup
    lib = Library.create("my_library")
    shape_collection = lib.get_shape_collection()
    shape_collection.graph.parse(
        data="""@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix : <urn:test#> .

:class1 a owl:Class ;
    rdfs:label "Class 1" ;
    skos:definition "This is class 1" .

:class2 a rdfs:Class ;
    rdfs:label "Class 2" .

:class3 a owl:Class .

:not_a_class a owl:NamedIndividual .

[ a owl:Class ] .
""",
        format="turtle",
    )

    # Act
    results = client.get(f"/libraries/{lib.id}/classes")

    # Assert
    assert results.status_code == 200

    expected_data = [
        {
            "uri": "urn:test#class1",
            "label": "Class 1",
            "definition": "This is class 1",
        },
        {"uri": "urn:test#class2", "label": "Class 2", "definition": None},
        {"uri": "urn:test#class3", "label": None, "definition": None},
    ]

    assert sorted(results.json, key=lambda x: x["uri"]) == sorted(
        expected_data, key=lambda x: x["uri"]
    )


def test_get_library_classes_not_found(client):
    # Act
    results = client.get("/libraries/-1/classes")

    # Assert
    assert results.status_code == 404
    assert results.json == {"message": "ID: -1"}


def test_get_library_subclasses(client, building_motif):
    # Setup
    lib = Library.create("my_library")
    shape_collection = lib.get_shape_collection()
    shape_collection.graph.parse(
        data="""@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix : <urn:test#> .
:parent a owl:Class ;
    rdfs:label "Parent" .
:child1 a owl:Class ;
    rdfs:subClassOf :parent ;
    rdfs:label "Child 1" .
:child2 a rdfs:Class ;
    rdfs:subClassOf :parent ;
    rdfs:label "Child 2" .
:grandchild1 a owl:Class ;
    rdfs:subClassOf :child1 ;
    rdfs:label "Grandchild 1" .
:unrelated a owl:Class ;
    rdfs:label "Unrelated" .
""",
        format="turtle",
    )

    # Act - get subclasses of :parent
    results = client.get(
        f"/libraries/{lib.id}/classes?subclasses_of={quote('urn:test#parent')}"
    )

    # Assert
    assert results.status_code == 200
    expected_data = [
        {"uri": "urn:test#child1", "label": "Child 1", "definition": None},
        {"uri": "urn:test#child2", "label": "Child 2", "definition": None},
        {"uri": "urn:test#grandchild1", "label": "Grandchild 1", "definition": None},
    ]
    assert sorted(results.json, key=lambda x: x["uri"]) == sorted(
        expected_data, key=lambda x: x["uri"]
    )

    # Act - get subclasses of :child1
    results = client.get(
        f"/libraries/{lib.id}/classes?subclasses_of={quote('urn:test#child1')}"
    )
    assert results.status_code == 200
    expected_data = [
        {"uri": "urn:test#grandchild1", "label": "Grandchild 1", "definition": None},
    ]
    assert results.json == expected_data

    # Act - get subclasses of unrelated (should be none)
    results = client.get(
        f"/libraries/{lib.id}/classes?subclasses_of={quote('urn:test#unrelated')}"
    )
    assert results.status_code == 200
    assert results.json == []

    # Act - get subclasses of grandchild1 (should be none)
    results = client.get(
        f"/libraries/{lib.id}/classes?subclasses_of={quote('urn:test#grandchild1')}"
    )
    assert results.status_code == 200
    assert results.json == []

    # Act - get subclasses of :parent with escaped URI
    escaped_uri = quote("urn:test#parent")
    results = client.get(f"/libraries/{lib.id}/classes?subclasses_of={escaped_uri}")

    # Assert
    assert results.status_code == 200
    expected_data = [
        {"uri": "urn:test#child1", "label": "Child 1", "definition": None},
        {"uri": "urn:test#child2", "label": "Child 2", "definition": None},
        {"uri": "urn:test#grandchild1", "label": "Grandchild 1", "definition": None},
    ]
    assert sorted(results.json, key=lambda x: x["uri"]) == sorted(
        expected_data, key=lambda x: x["uri"]
    )


def test_get_library_classes_server_error(client, building_motif):
    # Setup
    lib = Library.create("my_library")

    # Act
    with patch("buildingmotif.api.views.library.ShapeCollection.load") as mock_load:
        mock_sc = MagicMock()
        mock_sc.graph.query.side_effect = Exception("DB error")
        mock_load.return_value = mock_sc

        results = client.get(f"/libraries/{lib.id}/classes")

    # Assert
    assert results.status_code == 500
    assert results.json == {"message": "Internal Server Error"}


def test_get_library_shape_collection_ontology_name(client, building_motif):
    # Setup
    lib = Library.create("my_library")
    sc = lib.get_shape_collection()
    sc.graph.identifier = URIRef("urn:test:ontology")
    building_motif.session.commit()

    # Act
    results = client.get(f"/libraries/{lib.id}/shape_collection/ontology_name")

    # Assert
    assert results.status_code == 200
    assert results.json == {"ontology_name": "urn:test:ontology"}


def test_get_library_shape_collection_ontology_name_not_found(client):
    # Act
    results = client.get("/libraries/-1/shape_collection/ontology_name")

    # Assert
    assert results.status_code == 404
    assert results.json == {"message": "ID: -1"}
