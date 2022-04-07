import uuid

import pytest
from rdflib import Literal
from sqlalchemy.exc import NoResultFound

from buildingmotif.db_connections.table_connection import TableConnection
from buildingmotif.tables import DBTemplate


def make_tmp_table_connection(dir):
    temp_db_path = dir / "temp.db"
    uri = Literal(f"sqlite:///{temp_db_path}")

    return TableConnection(uri)


def test_create_db_template(tmpdir, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    tc = make_tmp_table_connection(tmpdir)

    db_template_library = tc.create_db_template_library(name="my_db_template_library")
    db_template = tc.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id
    )

    assert db_template.name == "my_db_template"
    assert db_template.body_id == str(mocked_uuid)
    assert db_template.template_library == db_template_library


def test_create_db_template_bad_template_library(tmpdir, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.create_db_template(
            name="my_db_template", template_library_id="i don't exist"
        )


def test_get_db_templates(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    my_db_template_library = tc.create_db_template_library(
        name="my_db_template_library"
    )
    tc.create_db_template(
        name="my_db_template", template_library_id=my_db_template_library.id
    )

    your_db_template_library = tc.create_db_template_library(
        name="your_db_template_library"
    )
    tc.create_db_template(
        name="your_db_template", template_library_id=your_db_template_library.id
    )

    db_templates = tc.get_all_db_templates()

    assert len(db_templates) == 2
    assert all(type(t) == DBTemplate for t in db_templates)
    assert set([t.name for t in db_templates]) == {"my_db_template", "your_db_template"}


def test_get_db_template(tmpdir, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    tc = make_tmp_table_connection(tmpdir)

    db_template_library = tc.create_db_template_library(name="my_db_template_library")
    db_template = tc.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id
    )

    db_template = tc.get_db_template(id=db_template.id)

    assert db_template.name == "my_db_template"
    assert db_template.body_id == str(mocked_uuid)
    assert db_template.template_library == db_template_library


def test_get_db_template_does_not_exist(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.get_db_template("I don't exist")


def test_update_db_template_name(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    db_template_library = tc.create_db_template_library(name="my_db_template_library")
    db_template = tc.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id
    )

    assert tc.get_db_template(db_template.id).name == "my_db_template"

    tc.update_db_template_name(db_template.id, "your_db_template")

    assert tc.get_db_template(db_template.id).name == "your_db_template"


def test_update_db_template_name_does_not_exist(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.update_db_template_name("I don't exist", "new_name")


def test_delete_db_template(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    db_template_library = tc.create_db_template_library(name="my_db_template_library")
    db_template = tc.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id
    )

    tc.delete_db_template(db_template.id)

    with pytest.raises(NoResultFound):
        tc.get_db_model(db_template.id)


def tests_delete_db_template_does_does_exist(tmpdir):
    tc = make_tmp_table_connection(tmpdir)

    with pytest.raises(NoResultFound):
        tc.delete_db_template("does not exist")
