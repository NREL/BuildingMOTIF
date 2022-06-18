import uuid

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

from buildingmotif import BuildingMOTIF
from buildingmotif.database.tables import DBTemplate


def create_dependacy_test_fixtures(bm: BuildingMOTIF):
    db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    dependant_template = bm.table_connection.create_db_template(
        name="dependant_template", template_library_id=db_template_library.id
    )
    dependee_template = bm.table_connection.create_db_template(
        name="dependee_template",
        template_library_id=db_template_library.id,
    )

    return (
        db_template_library,
        dependant_template,
        dependee_template,
    )


def test_create_db_template(bm: BuildingMOTIF, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = bm.table_connection.create_db_template(
        name="my_db_template",
        template_library_id=db_template_library.id,
    )

    assert db_template.name == "my_db_template"
    assert db_template.body_id == str(mocked_uuid)
    assert db_template.template_library == db_template_library


def test_create_db_template_bad_template_library(bm: BuildingMOTIF, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    with pytest.raises(NoResultFound):
        bm.table_connection.create_db_template(
            name="my_db_template",
            template_library_id=-999,  # id does not exist
        )


def test_create_template_bad_name(bm: BuildingMOTIF):
    db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    bm.table_connection.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id
    )

    with pytest.raises(Exception):
        bm.table_connection.create_db_template(
            name="my_db_template", template_library_id=db_template_library.id
        )

    bm.table_connection.bm.session.rollback()


def test_get_db_templates(bm: BuildingMOTIF):
    my_db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    bm.table_connection.create_db_template(
        name="my_db_template", template_library_id=my_db_template_library.id
    )

    your_db_template_library = bm.table_connection.create_db_template_library(
        name="your_db_template_library"
    )
    bm.table_connection.create_db_template(
        name="your_db_template",
        template_library_id=your_db_template_library.id,
    )

    db_templates = bm.table_connection.get_all_db_templates()

    assert len(db_templates) == 2
    assert all(type(t) == DBTemplate for t in db_templates)
    assert set([t.name for t in db_templates]) == {"my_db_template", "your_db_template"}


def test_get_db_template(bm: BuildingMOTIF, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = bm.table_connection.create_db_template(
        name="my_db_template",
        template_library_id=db_template_library.id,
    )

    db_template = bm.table_connection.get_db_template(id=db_template.id)

    assert db_template.name == "my_db_template"
    assert db_template.body_id == str(mocked_uuid)
    assert db_template.template_library == db_template_library


def test_get_db_template_does_not_exist(bm: BuildingMOTIF):
    with pytest.raises(NoResultFound):
        bm.table_connection.get_db_template(-999)


def test_update_db_template_name(bm: BuildingMOTIF):
    db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = bm.table_connection.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id
    )

    assert bm.table_connection.get_db_template(db_template.id).name == "my_db_template"

    bm.table_connection.update_db_template_name(db_template.id, "your_db_template")

    assert (
        bm.table_connection.get_db_template(db_template.id).name == "your_db_template"
    )


def test_update_db_template_name_bad_name(bm: BuildingMOTIF):
    db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    bm.table_connection.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id
    )

    bad_t = bm.table_connection.create_db_template(
        name="a fine name", template_library_id=db_template_library.id
    )
    bm.table_connection.update_db_template_name(bad_t.id, "my_db_template")

    with pytest.raises(Exception):
        bm.table_connection.bm.session.flush()

    bm.table_connection.bm.session.rollback()


def test_update_db_template_name_does_not_exist(bm: BuildingMOTIF):
    with pytest.raises(NoResultFound):
        bm.table_connection.update_db_template_name(-999, "new_name")


def test_delete_db_template(bm: BuildingMOTIF):
    db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = bm.table_connection.create_db_template(
        name="my_db_template", template_library_id=db_template_library.id
    )

    bm.table_connection.delete_db_template(db_template.id)

    with pytest.raises(NoResultFound):
        bm.table_connection.get_db_model(db_template.id)


def tests_delete_db_template_does_does_exist(bm: BuildingMOTIF):
    with pytest.raises(NoResultFound):
        bm.table_connection.delete_db_template(-999)


def test_add_template_dependency(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(bm)

    bm.table_connection.add_template_dependency(
        dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
    )

    assert dependant_template.dependencies == [dependee_template]
    assert dependee_template.dependants == [dependant_template]
    res = bm.table_connection.get_db_template_dependencies(dependant_template.id)
    assert len(res) == 1
    dep_assoc = res[0]
    assert dep_assoc.dependant_id == dependant_template.id
    assert dep_assoc.dependee_id == dependee_template.id
    assert dep_assoc.args == {"name": "ding", "h2": "dong"}


def test_add_template_dependency_bad_args(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(bm)

    with pytest.raises(ValueError):
        bm.table_connection.add_template_dependency(
            dependant_template.id, dependee_template.id, {"bad": "ding"}
        )


def test_add_template_dependency_already_exist(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(bm)

    bm.table_connection.add_template_dependency(
        dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
    )

    with pytest.raises(IntegrityError):
        bm.table_connection.add_template_dependency(
            dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
        )

    bm.table_connection.bm.session.rollback()


def test_get_dependencies(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(bm)

    bm.table_connection.add_template_dependency(
        dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
    )

    res = bm.table_connection.get_db_template_dependencies(dependant_template.id)
    assert len(res) == 1
    dep_assoc = res[0]
    assert dep_assoc.dependant_id == dependant_template.id
    assert dep_assoc.dependee_id == dependee_template.id
    assert dep_assoc.args == {"name": "ding", "h2": "dong"}


def test_remove_dependencies(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(bm)

    bm.table_connection.add_template_dependency(
        dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
    )

    res = bm.table_connection.get_db_template_dependencies(dependant_template.id)
    assert len(res) == 1
    dep_assoc = res[0]
    assert dep_assoc.dependant_id == dependant_template.id
    assert dep_assoc.dependee_id == dependee_template.id
    assert dep_assoc.args == {"name": "ding", "h2": "dong"}

    bm.table_connection.remove_template_dependency(
        dependant_template.id, dependee_template.id
    )

    assert bm.table_connection.get_db_template_dependencies(dependant_template.id) == ()


def test_remove_dependencies_does_not_exist(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependacy_test_fixtures(bm)

    with pytest.raises(NoResultFound):
        bm.table_connection.remove_template_dependency(
            dependant_template.id, dependee_template.id
        )

    bm.table_connection.bm.session.rollback()


def test_update_optional_args(bm: BuildingMOTIF):
    db_template_library = bm.table_connection.create_db_template_library(
        name="my_db_template_library"
    )
    db_template = bm.table_connection.create_db_template(
        name="my_db_template",
        template_library_id=db_template_library.id,
    )

    assert bm.table_connection.get_db_template(db_template.id).optional_args == []

    bm.table_connection.update_db_template_optional_args(db_template.id, ["a", "b"])

    assert bm.table_connection.get_db_template(db_template.id).optional_args == [
        "a",
        "b",
    ]
