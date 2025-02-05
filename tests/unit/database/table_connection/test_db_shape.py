import uuid

import pytest

from buildingmotif.database.errors import ShapeCollectionNotFound
from buildingmotif.database.tables import DBShapeCollection


def test_create_db_shape_collection(monkeypatch, table_connection):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_shape_collection = table_connection.create_db_shape_collection()

    assert db_shape_collection.graph_id == str(mocked_uuid)


def test_get_db_shape_collections(table_connection):
    shape_collection1 = table_connection.create_db_shape_collection()
    shape_collection2 = table_connection.create_db_shape_collection()

    db_shape_collections = table_connection.get_all_db_shape_collections()

    assert len(db_shape_collections) == 2
    assert all(type(m) == DBShapeCollection for m in db_shape_collections)
    assert set(db_shape_collections) == {shape_collection1, shape_collection2}


def test_get_db_shape_collection(table_connection, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_shape_collection = table_connection.create_db_shape_collection()
    db_shape_collection = table_connection.get_db_shape_collection(
        id=db_shape_collection.id
    )

    assert db_shape_collection.graph_id == str(mocked_uuid)


def test_get_db_shape_collection_does_not_exist(table_connection):
    with pytest.raises(ShapeCollectionNotFound):
        table_connection.get_db_shape_collection("I don't exist")


def test_delete_db_shape_collection(table_connection):
    db_shape_collection = table_connection.create_db_shape_collection()
    table_connection.delete_db_shape_collection(db_shape_collection.id)

    with pytest.raises(ShapeCollectionNotFound):
        table_connection.get_db_shape_collection(db_shape_collection.id)


def tests_delete_db_shape_collection_does_not_exist(table_connection):
    with pytest.raises(ShapeCollectionNotFound):
        table_connection.delete_db_shape_collection("does not exist")
