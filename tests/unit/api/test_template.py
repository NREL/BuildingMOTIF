from flask_api import status
from rdflib import Graph, Namespace

from buildingmotif.dataclasses import Library
from buildingmotif.namespaces import BRICK, A

BLDG = Namespace("urn:building/")


def test_get_all_templates(client, building_motif):
    # Setup
    lib = Library.create("my_library")
    lib.create_template("my_template")
    lib.create_template("your_template")

    # Act
    results = client.get("/templates")

    # Assert
    assert results.status_code == 200

    db_templates = building_motif.table_connection.get_all_db_templates()
    assert results.json == [
        {
            "id": t.id,
            "name": t.name,
            "body_id": t.body_id,
            "optional_args": t.optional_args,
            "library_id": t.library_id,
            "dependency_ids": [d.id for d in t.dependencies],
        }
        for t in db_templates
    ]


def test_get_template(client, building_motif):
    # Setup
    lib = Library.create("my_library")
    template = lib.create_template("my_template")

    # Act
    results = client.get(f"/templates/{template.id}")

    # Assert
    assert results.status_code == 200

    db_template = building_motif.table_connection.get_db_template_by_id(template.id)
    assert results.json == {
        "id": db_template.id,
        "name": db_template.name,
        "body_id": db_template.body_id,
        "optional_args": db_template.optional_args,
        "library_id": db_template.library_id,
        "dependency_ids": [d.id for d in db_template.dependencies],
    }


def test_get_template_with_parameters(client, building_motif):
    # Setup
    lib = Library.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")

    # Act
    results = client.get(f"/templates/{zone.id}?parameters=True")

    # Assert
    assert results.status_code == 200
    assert results.json["parameters"] == ["cav", "name"]


def test_get_template_not_found(client):
    # Act
    results = client.get("/templates/-1")

    # Assert
    assert results.status_code == 404
    assert results.json == {"message": "No template with id -1"}


def test_evaluate(client, building_motif):
    lib = Library.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    zone.inline_dependencies()
    assert zone.parameters == {"name", "cav"}

    results = client.post(
        f"/templates/{zone.id}/evaluate",
        json={"name": {"@id": BLDG["zone1"]}, "cav": {"@id": BLDG["cav1"]}},
    )

    assert results.status_code == status.HTTP_200_OK
    graph = Graph().parse(data=results.data, format="ttl")
    assert (BLDG["cav1"], A, BRICK.CAV) in graph
    assert (BLDG["zone1"], A, BRICK.HVAC_Zone) in graph
    assert (BLDG["zone1"], BRICK.isFedBy, BLDG["cav1"]) in graph
    assert len(list(graph.triples((None, None, None)))) == 3
