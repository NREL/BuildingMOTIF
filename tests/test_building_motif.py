from buildingmotif.building_motif import BuildingMotif


def test_load_library_from_ontology():
    bm = BuildingMotif("sqlite:///")
    lib = bm.load_library(ontology_graph="tests/fixtures/Brick1.3rc1-equip-only.ttl")
    assert lib is not None
    assert len(lib.get_templates()) == 344
    # spot check a certain template
    templ = lib.get_template_by_name("https://brickschema.org/schema/Brick#AHU")
    assert templ is not None
