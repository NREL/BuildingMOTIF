import uuid

import pytest
from rdflib import Literal
from sqlalchemy.exc import NoResultFound

from buildingmotif.db_connections.table_connection import TableConnection
from buildingmotif.tables import DBModel


def make_tmp_table_connection(dir):
    temp_db_path = dir / "temp.db"
    uri = Literal(f"sqlite:///{temp_db_path}")

    return TableConnection(uri)


def test_create_db_model(tmpdir, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    tc = make_tmp_table_connection(tmpdir)

    db_model = tc.create_db_model(name="my_db_model")

    assert db_model.name == "my_db_model"
    assert db_model.graph_id == str(mocked_uuid)


def test_get_db_models(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    tc.create_db_model(name="my_db_model")
    tc.create_db_model(name="your_db_model")

    db_models = tc.get_all_db_models()

    assert len(db_models) == 2
    assert all(type(m) == DBModel for m in db_models)
    assert set([m.name for m in db_models]) == {"my_db_model", "your_db_model"}


def test_get_db_model(tmpdir, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    tc = make_tmp_table_connection(tmpdir)

    db_model = tc.create_db_model(name="my_db_model")
    db_model = tc.get_db_model(id=db_model.id)

    assert db_model.name == "my_db_model"
    assert db_model.graph_id == str(mocked_uuid)


def test_get_db_model_does_not_exist(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.get_db_model("I don't exist")


def test_update_db_model_name(tmpdir):
    tc = make_tmp_table_connection(tmpdir)
    db_model_id = tc.create_db_model(name="my_db_model").id

    assert tc.get_db_model(db_model_id).name == "my_db_model"

    tc.update_db_model_name(db_model_id, "your_db_model")

    assert tc.get_db_model(db_model_id).name == "your_db_model"


def test_update_db_model_name_does_not_exist(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.update_db_model_name("I don't exist", "new_name")
