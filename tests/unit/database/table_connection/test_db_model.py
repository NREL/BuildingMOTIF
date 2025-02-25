import uuid
from unittest import mock

import pytest

from buildingmotif.database.errors import ModelNotFound, ShapeCollectionNotFound
from buildingmotif.database.tables import DBModel, DBShapeCollection


@mock.patch("uuid.uuid4")
def test_create_db_model(mock_uuid4, table_connection):
    mocked_graph_uuid = uuid.uuid4()
    mocked_manifest_uuid = uuid.uuid4()
    mock_uuid4.side_effect = [mocked_graph_uuid, mocked_manifest_uuid]

    db_model = table_connection.create_db_model(
        name="my_db_model", description="a very good model"
    )

    assert db_model.name == "my_db_model"
    assert db_model.description == "a very good model"
    assert db_model.graph_id == str(mocked_graph_uuid)
    assert isinstance(db_model.manifest, DBShapeCollection)
    assert db_model.manifest.graph_id == str(mocked_manifest_uuid)


def test_get_db_models(table_connection):
    table_connection.create_db_model(
        name="my_db_model", description="a very good model"
    )
    table_connection.create_db_model(
        name="your_db_model", description="an ok good model"
    )

    db_models = table_connection.get_all_db_models()

    assert len(db_models) == 2
    assert all(type(m) == DBModel for m in db_models)
    assert set([(m.name, m.description) for m in db_models]) == {
        ("my_db_model", "a very good model"),
        ("your_db_model", "an ok good model"),
    }


@mock.patch("uuid.uuid4")
def test_get_db_model(mock_uuid4, table_connection):
    mocked_graph_uuid = uuid.uuid4()
    mocked_manifest_uuid = uuid.uuid4()
    mock_uuid4.side_effect = [mocked_graph_uuid, mocked_manifest_uuid]

    db_model = table_connection.create_db_model(name="my_db_model")
    db_model = table_connection.get_db_model(id=db_model.id)

    assert db_model.name == "my_db_model"
    assert db_model.graph_id == str(mocked_graph_uuid)
    assert isinstance(db_model.manifest, DBShapeCollection)
    assert db_model.manifest.graph_id == str(mocked_manifest_uuid)


def test_get_db_model_does_not_exist(table_connection):
    with pytest.raises(ModelNotFound):
        table_connection.get_db_model("I don't exist")


def test_update_db_model_name(table_connection):
    db_model_id = table_connection.create_db_model(name="my_db_model").id

    assert table_connection.get_db_model(db_model_id).name == "my_db_model"

    table_connection.update_db_model_name(db_model_id, "your_db_model")

    assert table_connection.get_db_model(db_model_id).name == "your_db_model"


def test_update_db_model_name_does_not_exist(table_connection):
    with pytest.raises(ModelNotFound):
        table_connection.update_db_model_name("I don't exist", "new_name")


def test_update_db_model_description(table_connection):
    db_model_id = table_connection.create_db_model(
        name="name", description="a good model"
    ).id

    assert table_connection.get_db_model(db_model_id).description == "a good model"

    table_connection.update_db_model_description(db_model_id, "a great model")

    assert table_connection.get_db_model(db_model_id).description == "a great model"


def test_update_db_model_description_does_not_exist(table_connection):
    with pytest.raises(ModelNotFound):
        table_connection.update_db_model_description("I don't exist", "new_description")


def test_delete_db_model(table_connection):
    db_model = table_connection.create_db_model(name="my_db_model")
    table_connection.delete_db_model(db_model.id)

    with pytest.raises(ModelNotFound):
        table_connection.get_db_model(db_model.id)

    with pytest.raises(ShapeCollectionNotFound):
        table_connection.get_db_shape_collection(db_model.manifest.id)


def tests_delete_db_model_does_not_exist(table_connection):
    with pytest.raises(ModelNotFound):
        table_connection.delete_db_model("does not exist")
