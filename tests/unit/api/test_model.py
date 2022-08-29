from buildingmotif.dataclasses import Model


def test_get_all_models(client, building_motif):
    # Setup
    Model.create(name="my_model")
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
    }
