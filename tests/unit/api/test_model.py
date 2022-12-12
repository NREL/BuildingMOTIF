from rdflib import Graph, Namespace, URIRef
from rdflib.compare import isomorphic, to_isomorphic
from rdflib.namespace import RDF

from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import BRICK, A

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


def test_validate_model(client, building_motif):
    # Set up
    library = Library.load(ontology_graph="tests/unit/fixtures/shapes/shape1.ttl")
    assert library is not None

    BLDG = Namespace("urn:building/")
    model = Model.create(name=BLDG)
    model.add_triples((BLDG["vav1"], A, BRICK.VAV))

    # Action
    results = client.get(
        f"/models/{model.id}/validate",
        json={"library_id": library.id},
        headers={"Content-Type": "application/json"},
    )

    # Assert
    assert results.status_code == 200
    assert not results.get_json()["valid"]

    # Set up
    model.add_triples((BLDG["vav1"], A, BRICK.VAV))
    model.add_triples((BLDG["vav1"], BRICK.hasPoint, BLDG["temp_sensor"]))
    model.add_triples((BLDG["temp_sensor"], A, BRICK.Temperature_Sensor))
    model.add_triples((BLDG["vav1"], BRICK.hasPoint, BLDG["flow_sensor"]))
    model.add_triples((BLDG["flow_sensor"], A, BRICK.Air_Flow_Sensor))

    # Action
    results = client.get(
        f"/models/{model.id}/validate",
        json={"library_id": library.id},
        headers={"Content-Type": "application/json"},
    )

    # Assert
    assert results.status_code == 200
    assert results.get_json() == {
        "message": "Validation Report\nConforms: True\n",
        "valid": True,
    }


def test_validate_model_bad_model_id(client, building_motif):
    # Action
    results = client.get(
        f"/models/{-1}/validate",
        json={"library_id": -1},
        headers={"Content-Type": "application/json"},
    )

    # Assert
    assert results.status_code == 404


def test_validate_model_bad_content_type(client, building_motif):
    # Set up
    BLDG = Namespace("urn:building/")
    model = Model.create(name=BLDG)

    # Action
    results = client.get(
        f"/models/{model.id}/validate",
        data=graph_data,
        headers={"Content-Type": "application/xml"},
    )

    # Assert
    assert results.status_code == 400


def test_validate_model_bad_library_id(client, building_motif):
    # Set up
    BLDG = Namespace("urn:building/")
    model = Model.create(name=BLDG)

    # Action
    results = client.get(
        f"/models/{model.id}/validate",
        json={"library_id": -1},
        headers={"Content-Type": "application/json"},
    )

    # Assert
    assert results.status_code == 404
