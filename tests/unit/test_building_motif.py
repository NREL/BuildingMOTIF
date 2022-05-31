from buildingmotif import BuildingMOTIF


def test_load_library_from_ontology(bm: BuildingMOTIF):
    lib = bm.load_library(
        ontology_graph="tests/unit/fixtures/Brick1.3rc1-equip-only.ttl"
    )
    assert lib is not None
    assert len(lib.get_templates()) == 2
    # spot check a certain template
    templ = lib.get_template_by_name("https://brickschema.org/schema/Brick#AHU")
    assert templ is not None
    assert templ.parameters == {"name"}
    assert templ.head == ("name",)


def test_load_library_from_directory(bm: BuildingMOTIF):
    lib = bm.load_library(directory="tests/unit/fixtures/templates")
    assert lib is not None
    assert len(lib.get_templates()) == 6
    # spot check a certain template
    templ = lib.get_template_by_name("zone")
    assert templ is not None
    assert templ.parameters == {"zone", "cav"}
    assert sorted(templ.head) == sorted(("zone", "cav"))
