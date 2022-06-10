import pytest

from buildingmotif.dataclasses import TemplateLibrary


def test_create(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")

    assert tl.name == "my_template_library"
    assert isinstance(tl.id, int)

    also_tl = TemplateLibrary.load(tl.id)

    assert also_tl.name == "my_template_library"
    assert also_tl.id == tl.id


def test_update_name(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")

    assert tl.name == "my_template_library"

    tl.name = "a_new_name"
    assert tl.name == "a_new_name"


def test_update_id(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")

    with pytest.raises(AttributeError):
        tl.id = 1


def test_get_templates(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t1 = tl.create_template("my_template")
    t2 = tl.create_template("your_template")

    results = tl.get_templates()
    assert len(results) == 2
    assert [r.id for r in results] == [t1.id, t2.id]
