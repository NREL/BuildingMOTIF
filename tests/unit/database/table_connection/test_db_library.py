import uuid

import pytest
from sqlalchemy.exc import NoResultFound

from buildingmotif.database.tables import DBLibrary, DBShapeCollection, DBTemplate


def test_create_db_library(table_connection, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_library = table_connection.create_db_library(name="my_db_library")

    assert db_library.name == "my_db_library"
    assert db_library.templates == []
    assert isinstance(db_library.shape_collection, DBShapeCollection)
    assert db_library.shape_collection.graph_id == str(mocked_uuid)


def test_get_db_libraries(table_connection):
    table_connection.create_db_library(name="my_db_library")
    table_connection.create_db_library(name="your_db_library")

    db_libraries = table_connection.get_all_db_libraries()

    assert len(db_libraries) == 2
    assert all(type(tl) == DBLibrary for tl in db_libraries)
    assert set([tl.name for tl in db_libraries]) == {
        "my_db_library",
        "your_db_library",
    }


def test_get_db_library(table_connection):
    db_library = table_connection.create_db_library(name="my_library")
    table_connection.create_db_template("my_db_template", library_id=db_library.id)

    db_library = table_connection.get_db_library(id=db_library.id)
    assert db_library.name == "my_library"
    assert len(db_library.templates) == 1
    assert type(db_library.templates[0]) == DBTemplate
    assert db_library.templates[0].name == "my_db_template"


def test_get_db_library_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.get_db_library("I don't exist")


def test_get_db_library_by_name(table_connection):
    # create library  w/ template
    db_library = table_connection.create_db_library(name="my_library")
    table_connection.create_db_template("my_db_template", library_id=db_library.id)
    # get by name
    found = table_connection.get_db_library_by_name("my_library")
    assert found.name == "my_library"
    assert len(found.templates) == 1
    assert type(found.templates[0]) == DBTemplate
    assert found.templates[0].name == "my_db_template"


def test_get_db_library_by_name_not_found(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.get_db_library_by_name("I don't exist")


def test_update_db_library_name(table_connection):
    db_library_id = table_connection.create_db_library(name="my_db_library").id

    assert table_connection.get_db_library(db_library_id).name == "my_db_library"

    table_connection.update_db_library_name(db_library_id, "your_db_library")

    assert table_connection.get_db_library(db_library_id).name == "your_db_library"


def test_update_db_library_name_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.update_db_library_name("I don't exist", "new_name")


def test_delete_db_library(table_connection):
    db_library = table_connection.create_db_library(name="my_library")
    db_template = table_connection.create_db_template(
        "my_db_template", library_id=db_library.id
    )
    db_shape_collection = db_library.shape_collection

    table_connection.delete_db_library(db_library.id)

    with pytest.raises(NoResultFound):
        table_connection.get_db_library(db_library.id)

    with pytest.raises(NoResultFound):
        table_connection.get_db_template(db_template.id)

    with pytest.raises(NoResultFound):
        table_connection.get_db_shape_collection(db_shape_collection.id)


def tests_delete_db_library_does_does_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.delete_db_library("does not exist")
