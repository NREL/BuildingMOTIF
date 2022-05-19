import uuid

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

from buildingmotif.tables import DBTemplate


def create_dependacy_test_fixtures(table_connection):
    db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    dependant_template = table_connection.create_db_template(
        name="dependant_template", template_library_id=db_template_library.id, head=[]
    )
    dependee_template = table_connection.create_db_template(
        name="dependee_template",
        template_library_id=db_template_library.id,
        head=["h1", "h2"],
    )

    return (
        db_template_library,
        dependant_template,
        dependee_template,
    )


def test_create_db_template(table_connection, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = table_connection.create_db_template(
        name="my_db_template",
        template_library_id=db_template_library.id,
        head=["ding", "dong"],
    )

    assert db_template.name == "my_db_template"
    assert db_template.head == ("ding", "dong")
    assert db_template.body_id == str(mocked_uuid)
    assert db_template.template_library == db_template_library


def test_create_db_template_bad_template_library(table_connection, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    with pytest.raises(NoResultFound):
        table_connection.create_db_template(
            name="my_db_template", template_library_id="i don't exist", head=[]
        )


def test_create_template_bad_name(table_connection):
    db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    table_connection.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id, head=[]
    )

    with pytest.raises(Exception):
        table_connection.create_db_template(
            name="my_db_template", template_library_id=db_template_library.id, head=[]
        )

    table_connection.bm.session.rollback()


def test_get_db_templates(table_connection):
    my_db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    table_connection.create_db_template(
        name="my_db_template", template_library_id=my_db_template_library.id, head=[]
    )

    your_db_template_library = table_connection.create_db_template_library(
        name="your_db_template_library"
    )
    table_connection.create_db_template(
        name="your_db_template",
        template_library_id=your_db_template_library.id,
        head=[],
    )

    db_templates = table_connection.get_all_db_templates()

    assert len(db_templates) == 2
    assert all(type(t) == DBTemplate for t in db_templates)
    assert set([t.name for t in db_templates]) == {"my_db_template", "your_db_template"}


def test_get_db_template(table_connection, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = table_connection.create_db_template(
        name="my_db_template",
        template_library_id=db_template_library.id,
        head=["ding", "dong"],
    )

    db_template = table_connection.get_db_template(id=db_template.id)

    assert db_template.name == "my_db_template"
    assert db_template.head == ("ding", "dong")
    assert db_template.body_id == str(mocked_uuid)
    assert db_template.template_library == db_template_library


def test_get_db_template_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.get_db_template("I don't exist")


def test_update_db_template_name(table_connection):
    db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = table_connection.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id, head=[]
    )

    assert table_connection.get_db_template(db_template.id).name == "my_db_template"

    table_connection.update_db_template_name(db_template.id, "your_db_template")

    assert table_connection.get_db_template(db_template.id).name == "your_db_template"


def test_update_db_template_name_bad_name(table_connection):
    db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    table_connection.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id, head=[]
    )

    bad_t = table_connection.create_db_template(
        name="a fine name", template_library_id=db_template_library.id, head=[]
    )
    table_connection.update_db_template_name(bad_t.id, "my_db_template")

    with pytest.raises(Exception):
        table_connection.bm.session.flush()

    table_connection.bm.session.rollback()


def test_update_db_template_name_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.update_db_template_name("I don't exist", "new_name")


def test_delete_db_template(table_connection):
    db_template_library = table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = table_connection.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id, head=[]
    )

    table_connection.delete_db_template(db_template.id)

    with pytest.raises(NoResultFound):
        table_connection.get_db_model(db_template.id)


def tests_delete_db_template_does_does_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.delete_db_template("does not exist")


def test_add_template_dependency(table_connection):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(table_connection)

    table_connection.add_template_dependency(
        dependant_template.id, dependee_template.id, ["ding", "dong"]
    )

    assert dependant_template.dependencies == [dependee_template]
    assert dependee_template.dependants == [dependant_template]
    assert table_connection.get_db_tempalte_dependencies(dependant_template.id) == (
        (dependee_template.id, ("ding", "dong")),
    )


def test_add_template_dependency_bad_args(table_connection):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(table_connection)

    with pytest.raises(ValueError):
        table_connection.add_template_dependency(
            dependant_template.id, dependee_template.id, ["ding"]
        )


def test_add_template_dependency_already_exist(table_connection):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(table_connection)

    table_connection.add_template_dependency(
        dependant_template.id, dependee_template.id, ["ding", "dong"]
    )

    with pytest.raises(IntegrityError):
        table_connection.add_template_dependency(
            dependant_template.id, dependee_template.id, ["ding", "dong"]
        )

    table_connection.bm.session.rollback()


def test_get_dependencies(table_connection):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(table_connection)

    table_connection.add_template_dependency(
        dependant_template.id, dependee_template.id, ["ding", "dong"]
    )

    assert table_connection.get_db_tempalte_dependencies(dependant_template.id) == (
        (dependee_template.id, ("ding", "dong")),
    )


def test_remove_dependencies(table_connection):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(table_connection)

    table_connection.add_template_dependency(
        dependant_template.id, dependee_template.id, ["ding", "dong"]
    )

    assert table_connection.get_db_tempalte_dependencies(dependant_template.id) == (
        (dependee_template.id, ("ding", "dong")),
    )

    table_connection.remove_template_dependency(
        dependant_template.id, dependee_template.id
    )

    assert table_connection.get_db_tempalte_dependencies(dependant_template.id) == ()


def test_remove_dependencies_does_not_exist(table_connection):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(table_connection)

    with pytest.raises(NoResultFound):
        table_connection.remove_template_dependency(
            dependant_template.id, dependee_template.id
        )

    table_connection.bm.session.rollback()
