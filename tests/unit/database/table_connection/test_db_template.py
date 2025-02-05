import uuid

import pytest
import rdflib
from sqlalchemy.exc import IntegrityError, NoResultFound

from buildingmotif import BuildingMOTIF
from buildingmotif.database.errors import LibraryNotFound, TemplateNotFound
from buildingmotif.database.tables import DBTemplate


def create_dependency_test_fixtures(bm: BuildingMOTIF):
    dependant_template_body = rdflib.Graph()
    dependant_template_body.parse(
        data="""@prefix P: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    P:name a brick:VAV ;
        brick:nothing P:ding ;
        brick:nothing2  P:dong .
    """,
        format="turtle",
    )

    dependency_template_body = rdflib.Graph()
    dependency_template_body.parse(
        data="""@prefix P: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    P:name a brick:Temperature_Sensor ;
        brick:hasUnit P:h2 .
    """,
        format="turtle",
    )
    db_library = bm.table_connection.create_db_library(name="my_db_library")
    dependant_template = bm.table_connection.create_db_template(
        name="dependant_template", library_id=db_library.id
    )
    body = bm.graph_connection.get_graph(dependant_template.body_id)
    body += dependant_template_body

    dependee_template = bm.table_connection.create_db_template(
        name="dependee_template",
        library_id=db_library.id,
    )
    body = bm.graph_connection.get_graph(dependee_template.body_id)
    body += dependency_template_body

    return (
        db_library,
        dependant_template,
        dependee_template,
    )


def test_create_db_template(bm: BuildingMOTIF, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    db_library = bm.table_connection.create_db_library(name="my_db_library")
    db_template = bm.table_connection.create_db_template(
        name="my_db_template",
        library_id=db_library.id,
    )

    assert db_template.name == "my_db_template"
    assert db_template.body_id == str(mocked_uuid)
    assert db_template.library == db_library


def test_create_db_template_bad_library(bm: BuildingMOTIF, monkeypatch):
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    with pytest.raises(LibraryNotFound):
        bm.table_connection.create_db_template(
            name="my_db_template",
            library_id=-999,  # id does not exist
        )


def test_create_template_bad_name(bm: BuildingMOTIF):
    db_library = bm.table_connection.create_db_library(name="my_db_library")
    bm.table_connection.create_db_template(
        name="my_db_template", library_id=db_library.id
    )

    with pytest.raises(Exception):
        bm.table_connection.create_db_template(
            name="my_db_template", library_id=db_library.id
        )

    bm.table_connection.bm.session.rollback()


def test_get_db_templates(bm: BuildingMOTIF):
    my_db_library = bm.table_connection.create_db_library(name="my_db_library")
    bm.table_connection.create_db_template(
        name="my_db_template", library_id=my_db_library.id
    )

    your_db_library = bm.table_connection.create_db_library(name="your_db_library")
    bm.table_connection.create_db_template(
        name="your_db_template",
        library_id=your_db_library.id,
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

    db_library = bm.table_connection.create_db_library(name="my_db_library")
    db_template = bm.table_connection.create_db_template(
        name="my_db_template",
        library_id=db_library.id,
    )

    db_template = bm.table_connection.get_db_template(id=db_template.id)

    assert db_template.name == "my_db_template"
    assert db_template.body_id == str(mocked_uuid)
    assert db_template.library == db_library


def test_get_db_template_does_not_exist(bm: BuildingMOTIF):
    with pytest.raises(TemplateNotFound):
        bm.table_connection.get_db_template(-999)


def test_update_db_template_name(bm: BuildingMOTIF):
    db_library = bm.table_connection.create_db_library(name="my_db_library")
    db_template = bm.table_connection.create_db_template(
        name="my_db_template", library_id=db_library.id
    )

    assert bm.table_connection.get_db_template(db_template.id).name == "my_db_template"

    bm.table_connection.update_db_template_name(db_template.id, "your_db_template")

    assert (
        bm.table_connection.get_db_template(db_template.id).name == "your_db_template"
    )


def test_update_db_template_name_bad_name(bm: BuildingMOTIF):
    db_library = bm.table_connection.create_db_library(name="my_db_library")
    bm.table_connection.create_db_template(
        name="my_db_template", library_id=db_library.id
    )

    bad_t = bm.table_connection.create_db_template(
        name="a fine name", library_id=db_library.id
    )
    bm.table_connection.update_db_template_name(bad_t.id, "my_db_template")

    with pytest.raises(Exception):
        bm.table_connection.bm.session.flush()

    bm.table_connection.bm.session.rollback()


def test_update_db_template_name_does_not_exist(bm: BuildingMOTIF):
    with pytest.raises(TemplateNotFound):
        bm.table_connection.update_db_template_name(-999, "new_name")


def test_delete_db_template(bm: BuildingMOTIF):
    db_library = bm.table_connection.create_db_library(name="my_db_library")
    db_template = bm.table_connection.create_db_template(
        name="my_db_template", library_id=db_library.id
    )

    bm.table_connection.delete_db_template(db_template.id)

    with pytest.raises(TemplateNotFound):
        bm.table_connection.get_db_template(db_template.id)


def tests_delete_db_template_does_does_exist(bm: BuildingMOTIF):
    with pytest.raises(TemplateNotFound):
        bm.table_connection.delete_db_template(-999)


def test_add_template_dependency(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependency_test_fixtures(bm)

    bm.table_connection.add_template_dependency_preliminary(
        dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
    )
    bm.table_connection.check_all_template_dependencies()

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
    ) = create_dependency_test_fixtures(bm)

    with pytest.raises(ValueError):
        bm.table_connection.add_template_dependency_preliminary(
            dependant_template.id, dependee_template.id, {"bad": "ding"}
        )
        bm.table_connection.check_all_template_dependencies()


def test_add_template_dependency_already_exist(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependency_test_fixtures(bm)

    bm.table_connection.add_template_dependency_preliminary(
        dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
    )

    with pytest.raises(IntegrityError):
        bm.table_connection.add_template_dependency_preliminary(
            dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
        )
        bm.table_connection.check_all_template_dependencies()

    bm.table_connection.bm.session.rollback()


def test_get_dependencies(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependency_test_fixtures(bm)

    bm.table_connection.add_template_dependency_preliminary(
        dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
    )
    bm.table_connection.check_all_template_dependencies()

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
    ) = create_dependency_test_fixtures(bm)

    bm.table_connection.add_template_dependency_preliminary(
        dependant_template.id, dependee_template.id, {"name": "ding", "h2": "dong"}
    )
    bm.table_connection.check_all_template_dependencies()

    res = bm.table_connection.get_db_template_dependencies(dependant_template.id)
    assert len(res) == 1
    dep_assoc = res[0]
    assert dep_assoc.dependant_id == dependant_template.id
    assert dep_assoc.dependee_id == dependee_template.id
    assert dep_assoc.args == {"name": "ding", "h2": "dong"}

    bm.table_connection.delete_template_dependency(
        dependant_template.id, dependee_template.id
    )

    assert bm.table_connection.get_db_template_dependencies(dependant_template.id) == ()


def test_remove_dependencies_does_not_exist(bm: BuildingMOTIF):
    (
        _,
        dependant_template,
        dependee_template,
    ) = create_dependency_test_fixtures(bm)

    with pytest.raises(NoResultFound):
        bm.table_connection.delete_template_dependency(
            dependant_template.id, dependee_template.id
        )

    bm.table_connection.bm.session.rollback()


def test_update_optional_args(bm: BuildingMOTIF):
    db_library = bm.table_connection.create_db_library(name="my_db_library")
    db_template = bm.table_connection.create_db_template(
        name="my_db_template",
        library_id=db_library.id,
    )

    assert bm.table_connection.get_db_template(db_template.id).optional_args == []

    bm.table_connection.update_db_template_optional_args(db_template.id, ["a", "b"])

    assert bm.table_connection.get_db_template(db_template.id).optional_args == [
        "a",
        "b",
    ]
