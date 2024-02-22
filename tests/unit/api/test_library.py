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
    assert results.json == {"message": "No library with id -1"}
