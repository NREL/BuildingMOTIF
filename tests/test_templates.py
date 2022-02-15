from pathlib import Path

from rdflib import Graph, Namespace

from buildingmotif.template import TemplateLibrary

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures/templates"
BLDG = Namespace("urn:bldg#")
more_ns = {"bldg": str(BLDG)}


def test_make_library():
    lib = TemplateLibrary(FIXTURES_DIR / "1.yml")
    assert len(lib.templates) == 3
    assert len(lib["outside-air-damper"]) == 2
    assert len(lib["supply-fan"]) == 1
    assert len(lib["single-zone-vav-ahu"]) == 1

    lib = TemplateLibrary(FIXTURES_DIR / "2.yml")
    assert len(lib.templates) == 2
    assert len(lib["vav"]) == 1
    assert len(lib["temp-sensor"]) == 1


def test_full_template_evaluations_no_deps():
    lib = TemplateLibrary(FIXTURES_DIR / "2.yml")
    temp_sensor_template = lib["temp-sensor"][0]
    assert temp_sensor_template.parameters == {"name"}
    result = temp_sensor_template.evaluate(
        {"name": "bldg:temp-sensor-1"}, more_namespaces=more_ns
    )
    assert isinstance(result, Graph)
    assert len(result) == 1


def test_full_template_evaluations_with_deps():
    lib = TemplateLibrary(FIXTURES_DIR / "2.yml")
    vav_template = lib["vav"][0]
    # TODO: should inline_dependencies be called automatically?
    vav_template.inline_dependencies()
    assert vav_template.parameters == {"name", "zone", "sen"}
    result = vav_template.evaluate(
        {
            "zone": "bldg:zone1",
            "sen": "bldg:temp-sensor-1",
            "name": "bldg:temp-sensor-1",
        },
        more_namespaces=more_ns,
    )
    assert isinstance(result, Graph)
    assert len(result) == 4
