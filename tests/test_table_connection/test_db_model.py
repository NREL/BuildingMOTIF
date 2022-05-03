import uuid

import pytest
from sqlalchemy.exc import NoResultFound

from buildingmotif.tables import DBModel


def test_create_db_model(monkeypatch, table_connection):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_model = table_connection.create_db_model(name="my_db_model")

    assert db_model.name == "my_db_model"
    assert db_model.graph_id == str(mocked_uuid)


def test_get_db_models(table_connection):
    table_connection.create_db_model(name="my_db_model")
    table_connection.create_db_model(name="your_db_model")

    db_models = table_connection.get_all_db_models()

    assert len(db_models) == 2
    assert all(type(m) == DBModel for m in db_models)
    assert set([m.name for m in db_models]) == {"my_db_model", "your_db_model"}


def test_get_db_model(table_connection, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_model = table_connection.create_db_model(name="my_db_model")
    db_model = table_connection.get_db_model(id=db_model.id)

    assert db_model.name == "my_db_model"
    assert db_model.graph_id == str(mocked_uuid)


def test_get_db_model_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.get_db_model("I don't exist")


def test_update_db_model_name(table_connection):
    db_model_id = table_connection.create_db_model(name="my_db_model").id

    assert table_connection.get_db_model(db_model_id).name == "my_db_model"

    table_connection.update_db_model_name(db_model_id, "your_db_model")

    assert table_connection.get_db_model(db_model_id).name == "your_db_model"


def test_update_db_model_name_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.update_db_model_name("I don't exist", "new_name")


def test_delete_db_model(table_connection):
    db_model = table_connection.create_db_model(name="my_db_model")
    table_connection.delete_db_model(db_model.id)

    with pytest.raises(NoResultFound):
        table_connection.get_db_model(db_model.id)


def tests_delete_db_model_does_does_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.delete_db_model("does not exist")
