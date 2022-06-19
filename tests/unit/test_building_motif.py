from pathlib import Path

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import TemplateLibrary
from tests.unit.conftest import MockTemplateLibrary


def test_load_library_from_ontology(bm: BuildingMOTIF):
    lib = TemplateLibrary.load(
        ontology_graph="tests/unit/fixtures/Brick1.3rc1-equip-only.ttl"
    )
    assert lib is not None
    assert len(lib.get_templates()) == 2
    # spot check a certain template
    templ = lib.get_template_by_name("https://brickschema.org/schema/Brick#AHU")
    assert templ is not None
    assert templ.parameters == {"name"}


def test_load_library_from_directory(bm: BuildingMOTIF):
    lib = TemplateLibrary.load(directory="tests/unit/fixtures/templates")
    assert lib is not None
    assert len(lib.get_templates()) == 7
    # spot check a certain template
    templ = lib.get_template_by_name("zone")
    assert templ is not None
    assert templ.parameters == {"name", "cav"}


def test_libraries(bm: BuildingMOTIF, library: str):
    """
    Ensures that the libraries can be loaded and used
    """
    # Brick dependencies always resolve for the test library
    setattr(TemplateLibrary, "load", MockTemplateLibrary.load)
    MockTemplateLibrary.create("https://brickschema.org/schema/1.3/Brick")
    lib = TemplateLibrary._load_from_directory(Path(library))
    assert lib is not None
