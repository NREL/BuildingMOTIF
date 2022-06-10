import pytest
from sqlalchemy.exc import NoResultFound

from buildingmotif.database.tables import DBTemplate, DBTemplateLibrary


def test_create_db_template_library(table_connection):
    db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )

    assert db_template_library.name == "my_db_template_library"
    assert db_template_library.templates == []


def test_get_db_template_libraries(table_connection):
    table_connection.create_db_template_library(name="my_db_template_library")
    table_connection.create_db_template_library(name="your_db_template_library")

    db_template_libraries = table_connection.get_all_db_template_libraries()

    assert len(db_template_libraries) == 2
    assert all(type(tl) == DBTemplateLibrary for tl in db_template_libraries)
    assert set([tl.name for tl in db_template_libraries]) == {
        "my_db_template_library",
        "your_db_template_library",
    }


def test_get_db_template_library(table_connection):
    db_template_library = table_connection.create_db_template_library(
        name="my_template_library"
    )
    table_connection.create_db_template(
        "my_db_template", template_library_id=db_template_library.id
    )

    db_template_library = table_connection.get_db_template_library(
        id=db_template_library.id
    )
    assert db_template_library.name == "my_template_library"
    assert len(db_template_library.templates) == 1
    assert type(db_template_library.templates[0]) == DBTemplate
    assert db_template_library.templates[0].name == "my_db_template"


def test_get_db_template_library_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.get_db_template_library("I don't exist")


def test_update_db_template_library_name(table_connection):
    db_template_library_id = table_connection.create_db_template_library(
        name="my_db_template_library"
    ).id

    assert (
        table_connection.get_db_template_library(db_template_library_id).name
        == "my_db_template_library"
    )

    table_connection.update_db_template_library_name(
        db_template_library_id, "your_db_template_library"
    )

    assert (
        table_connection.get_db_template_library(db_template_library_id).name
        == "your_db_template_library"
    )


def test_update_db_template_library_name_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.update_db_template_library_name("I don't exist", "new_name")


def test_delete_db_template_library(table_connection):
    db_template_library = table_connection.create_db_template_library(
        name="my_template_library"
    )
    db_template = table_connection.create_db_template(
        "my_db_template", template_library_id=db_template_library.id
    )

    table_connection.delete_db_template_library(db_template_library.id)

    with pytest.raises(NoResultFound):
        table_connection.get_db_template_library(db_template_library.id)

    with pytest.raises(NoResultFound):
        table_connection.get_db_template(db_template.id)


def tests_delete_db_template_library_does_does_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.delete_db_template_library("does not exist")
