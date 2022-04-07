import pytest
from rdflib import Literal
from sqlalchemy.exc import NoResultFound

from buildingmotif.db_connections.table_connection import TableConnection
from buildingmotif.tables import DBTemplate, DBTemplateLibrary


def make_tmp_table_connection(dir):
    temp_db_path = dir / "temp.db"
    uri = Literal(f"sqlite:///{temp_db_path}")

    return TableConnection(uri)


def test_create_db_template_library(tmpdir, monkeypatch):
    tc = make_tmp_table_connection(tmpdir)

    db_template_library = tc.create_db_template_library(name="my_db_template_library")

    assert db_template_library.name == "my_db_template_library"
    assert db_template_library.templates == []


def test_get_db_template_libraries(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    tc.create_db_template_library(name="my_db_template_library")
    tc.create_db_template_library(name="your_db_template_library")

    db_template_libraries = tc.get_all_db_template_library()

    assert len(db_template_libraries) == 2
    assert all(type(tl) == DBTemplateLibrary for tl in db_template_libraries)
    assert set([tl.name for tl in db_template_libraries]) == {
        "my_db_template_library",
        "your_db_template_library",
    }


def test_get_db_template_library(tmpdir, monkeypatch):
    tc = make_tmp_table_connection(tmpdir)

    db_template_library = tc.create_db_template_library(name="my_template_library")
    tc.create_db_template("my_db_template", template_library_id=db_template_library.id)

    db_template_library = tc.get_db_template_library(id=db_template_library.id)
    assert db_template_library.name == "my_template_library"
    assert len(db_template_library.templates) == 1
    assert type(db_template_library.templates[0]) == DBTemplate
    assert db_template_library.templates[0].name == "my_db_template"


def test_get_db_template_library_does_not_exist(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.get_db_template_library("I don't exist")


def test_update_db_template_library_name(tmpdir):
    tc = make_tmp_table_connection(tmpdir)
    db_template_library_id = tc.create_db_template_library(
        name="my_db_template_library"
    ).id

    assert (
        tc.get_db_template_library(db_template_library_id).name
        == "my_db_template_library"
    )

    tc.update_db_template_library_name(
        db_template_library_id, "your_db_template_library"
    )

    assert (
        tc.get_db_template_library(db_template_library_id).name
        == "your_db_template_library"
    )


def test_update_db_template_library_name_does_not_exist(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.update_db_template_library_name("I don't exist", "new_name")


def test_delete_db_template_library(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    db_template_library = tc.create_db_template_library(name="my_template_library")
    db_template = tc.create_db_template(
        "my_db_template", template_library_id=db_template_library.id
    )

    tc.delete_db_template_library(db_template_library.id)

    with pytest.raises(NoResultFound):
        tc.get_db_template_library(db_template_library.id)

    with pytest.raises(NoResultFound):
        tc.get_db_template(db_template.id)


def tests_delete_db_template_library_does_does_exist(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.delete_db_template_library("does not exist")
