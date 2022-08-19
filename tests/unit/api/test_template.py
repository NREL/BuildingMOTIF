from buildingmotif.dataclasses import Library


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
