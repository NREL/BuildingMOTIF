from rdflib import Graph, URIRef
from rdflib.compare import isomorphic, to_isomorphic
from rdflib.namespace import RDF

from buildingmotif.dataclasses import Model

graph_data = """
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

default_graph = [
    (URIRef("my_model"), RDF.type, URIRef("http://www.w3.org/2002/07/owl#Ontology"))
]


def test_get_all_models(client, building_motif):
    # Setup
    Model.create(name="my_model", description="the best model")
    Model.create(name="your_model")

    # Act
    results = client.get("/models")

    # Assert
    assert results.status_code == 200

    db_models = building_motif.table_connection.get_all_db_models()
    assert results.json == [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "graph_id": m.graph_id,
        }
        for m in db_models
    ]


def test_get_model(client, building_motif):
    # Setup
    model = Model.create(name="my_model")

    # Act
    results = client.get(f"/models/{model.id}")

    # Assert
    assert results.status_code == 200

    db_model = building_motif.table_connection.get_db_model(model.id)
    assert results.json == {
        "id": db_model.id,
        "name": db_model.name,
        "graph_id": db_model.graph_id,
        "description": db_model.description,
    }


def test_get_model_not_found(client):
    # Act
    results = client.get("/models/-1")

    # Assert
    assert results.status_code == 404
    assert results.json == {"message": "No model with id -1"}


def test_get_model_graph(client, building_motif):
    # Setup
    model = Model.create(name="urn:my_model")
    model.add_graph(Graph().parse(data=graph_data, format="ttl"))
    excepted_graph = to_isomorphic(model.graph)
    building_motif.session.commit()

    # Act
    results = client.get(f"/models/{model.id}/graph")

    # Assert
    assert results.status_code == 200
    results_graph = Graph().parse(data=results.data, format="ttl")
    assert isomorphic(results_graph, excepted_graph)


def test_get_model_graph_not_found(client):
    # Act
    results = client.get("/models/-1/graph")

    # Assert
    assert results.status_code == 404
    assert results.json == {"message": "No model with id -1"}


def test_update_model_graph(client, building_motif):
    # Set up
    model = Model.create(name="my_model")
    assert isomorphic(model.graph, default_graph)

    # Action
    results = client.patch(
        f"/models/{model.id}/graph",
        data=graph_data,
        headers={"Content-Type": "application/xml"},
    )
    model = Model.load(model.id)

    # Assert
    assert results.status_code == 200
    results_graph = Graph().parse(data=results.data, format="ttl")
    expected_graph = Graph().parse(data=graph_data, format="ttl")
    assert isomorphic(results_graph, expected_graph)
    assert isomorphic(model.graph, expected_graph)


def test_update_model_graph_not_found(client, building_motif):
    # Act
    results = client.patch(
        "/models/-1/graph", data=graph_data, headers={"Content-Type": "application/xml"}
    )

    # Assert
    assert results.status_code == 404
    assert results.json == {"message": "No model with id -1"}


def test_update_model_graph_no_header(client, building_motif):
    # Set up
    model = Model.create(name="my_model")
    assert isomorphic(model.graph, default_graph)

    # Action
    results = client.patch(f"/models/{model.id}/graph", data=graph_data)

    # Assert
    assert results.status_code == 400


def test_update_model_graph_bad_graph_value(client, building_motif):
    # Set up
    model = Model.create(name="my_model")
    assert isomorphic(model.graph, default_graph)

    # Action
    results = client.patch(
        f"/models/{model.id}/graph",
        data="not xml",
        headers={"Content-Type": "application/xml"},
    )

    # Assert
    assert results.status_code == 400
