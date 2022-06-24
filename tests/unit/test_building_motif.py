from pathlib import Path
from typing import Optional

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
    # check that Brick was loaded as a shape collection
    shapeg = lib.get_shape_collection()
    assert shapeg is not None
    assert len(shapeg.graph) > 1


def test_load_library_from_directory(bm: BuildingMOTIF):
    lib = TemplateLibrary.load(directory="tests/unit/fixtures/templates")
    assert lib is not None
    assert len(lib.get_templates()) == 7
    # spot check a certain template
    templ = lib.get_template_by_name("zone")
    assert templ is not None
    assert templ.parameters == {"name", "cav"}


def test_load_library_from_directory_with_shapes(bm: BuildingMOTIF):
    lib = TemplateLibrary.load(directory="tests/unit/fixtures")
    assert lib is not None
    shapeg = lib.get_shape_collection()
    assert shapeg is not None
    assert len(shapeg.graph) > 1


def test_libraries(monkeypatch, bm: BuildingMOTIF, library: str):
    """
    Ensures that the libraries can be loaded and used
    """
    original_load = TemplateLibrary.load

    def mock_load(
        db_id: Optional[int] = None,
        ontology_graph: Optional[str] = None,
        directory: Optional[str] = None,
        name: Optional[str] = None,
    ):
        if name is not None:
            try:
                db_template_library = (
                    bm.table_connection.get_db_template_library_by_name(name)
                )
                return MockTemplateLibrary(
                    _id=db_template_library.id, _name=db_template_library.name, _bm=bm
                )
            except Exception:
                return MockTemplateLibrary.create(name)
        else:
            original_load(db_id, ontology_graph, directory, name)

    monkeypatch.setattr(TemplateLibrary, "load", mock_load)
    # Brick dependencies always resolve for the test library
    MockTemplateLibrary.create("https://brickschema.org/schema/1.3/Brick")
    lib = TemplateLibrary._load_from_directory(Path(library))
    assert lib is not None
