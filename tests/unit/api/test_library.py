from rdflib import URIRef

from buildingmotif.dataclasses import Library
from buildingmotif.namespaces import RDF, RDFS, SH, SKOS


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
    # Setup
    my_library = Library.create("my_library")
    my_library.get_shape_collection().add_graph(
        [
            (URIRef("my_shape"), RDF.type, SH.NodeShape),
            (URIRef("my_shape"), RDFS.label, URIRef("my shape label")),
            (URIRef("my_shape"), SKOS.description, URIRef("my shape description")),
            (URIRef("my_other_shape"), RDF.type, SH.NodeShape),
            (URIRef("my_other_shape"), RDFS.label, URIRef("my shape other label")),
            (
                URIRef("my_other_shape"),
                SKOS.description,
                URIRef("my shape other description"),
            ),
        ]
    )
    your_library = Library.create("your_library")
    your_library.get_shape_collection().add_graph(
        [
            (URIRef("your_shape"), RDF.type, SH.NodeShape),
            (URIRef("your_shape"), RDFS.label, URIRef("your shape label")),
            (URIRef("your_shape"), SKOS.description, URIRef("your shape description")),
        ]
    )

    # Act
    results = client.get("/libraries/shapes")

    # Assert
    assert results.status_code == 200
    assert results.json == [
        {
            "library_name": "my_library",
            "library_id": my_library.id,
            "uri": "my_shape",
            "label": "my shape label",
            "description": "my shape description",
        },
        {
            "library_name": "my_library",
            "library_id": my_library.id,
            "uri": "my_other_shape",
            "label": "my shape other label",
            "description": "my shape other description",
        },
        {
            "library_name": "your_library",
            "library_id": your_library.id,
            "uri": "your_shape",
            "label": "your shape label",
            "description": "your shape description",
        },
    ]


def test_get_library(client, building_motif):
    # Setup
    lib = Library.create("my_library")
    lib.create_template("my_template")

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


def test_get_library_not_found(client):
    # Act
    results = client.get("/libraries/-1")

    # Assert
    assert results.status_code == 404
    assert results.json == {"message": "No library with id -1"}
