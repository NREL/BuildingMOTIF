from rdflib import Graph

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
    # Setup
    my_library = Library.create("my_library")
    shape_graph_ttl = """
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix : <urn:ex/> .
    :my_shape a sh:NodeShape ;
        sh:targetClass brick:Entity ;
        rdfs:label "my shape label" ;
        skos:description "my shape description" .
    :my_other_shape a sh:NodeShape ;
        sh:targetClass brick:Entity ;
        rdfs:label "my shape other label" ;
        skos:description "my shape other description" .
    """
    g = Graph()
    g.parse(data=shape_graph_ttl)
    my_library.get_shape_collection().add_graph(g)

    shape_graph_ttl = """
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix : <urn:ex/> .
    :your_shape a sh:NodeShape ;
        sh:targetClass brick:Entity ;
        rdfs:label "your shape label" ;
        skos:description "your shape description" .
    """
    g = Graph()
    g.parse(data=shape_graph_ttl)
    your_library = Library.create("your_library")
    your_library.get_shape_collection().add_graph(g)

    # Act
    results = client.get("/libraries/shapes")

    # Assert
    assert results.status_code == 200
    expected = sorted(
        [
            {
                "library_name": "my_library",
                "library_id": my_library.id,
                "uri": "urn:ex/my_shape",
                "label": "my shape label",
                "description": "my shape description",
            },
            {
                "library_name": "my_library",
                "library_id": my_library.id,
                "uri": "urn:ex/my_other_shape",
                "label": "my shape other label",
                "description": "my shape other description",
            },
            {
                "library_name": "your_library",
                "library_id": your_library.id,
                "uri": "urn:ex/your_shape",
                "label": "your shape label",
                "description": "your shape description",
            },
        ],
        key=lambda x: x["uri"],
    )
    actual = sorted(results.json, key=lambda x: x["uri"])
    assert expected == actual


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
