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


def test_get_library(client, building_motif):
    # Setup
    lib = Library.create("my_library")

    # Act
    results = client.get(f"/libraries/{lib.id}")

    # Assert
    assert results.status_code == 200

    db_library = building_motif.table_connection.get_db_library_by_id(lib.id)
    assert results.json == {
        "id": db_library.id,
        "name": db_library.name,
        "template_ids": [t.id for t in db_library.templates],
        "shape_collection_id": db_library.shape_collection_id,
    }
