import uuid

import pytest
from sqlalchemy.exc import NoResultFound

from buildingmotif.database.tables import DBShape


def test_create_db_shape(monkeypatch, table_connection):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_shape = table_connection.create_db_shape()

    assert db_shape.graph_id == str(mocked_uuid)


def test_get_db_shapes(table_connection):
    shape1 = table_connection.create_db_shape()
    shape2 = table_connection.create_db_shape()

    db_shapes = table_connection.get_all_db_shapes()

    assert len(db_shapes) == 2
    assert all(type(m) == DBShape for m in db_shapes)
    assert set(db_shapes) == {shape1, shape2}


def test_get_db_shape(table_connection, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_shape = table_connection.create_db_shape()
    db_shape = table_connection.get_db_shape(id=db_shape.id)

    assert db_shape.graph_id == str(mocked_uuid)


def test_get_db_shape_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.get_db_shape("I don't exist")


def test_delete_db_shape(table_connection):
    db_shape = table_connection.create_db_shape()
    table_connection.delete_db_shape(db_shape.id)

    with pytest.raises(NoResultFound):
        table_connection.get_db_shape(db_shape.id)


def tests_delete_db_shape_does_does_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.delete_db_shape("does not exist")
