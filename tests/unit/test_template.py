from pathlib import Path

import pytest
from rdflib import Graph, Namespace

from buildingmotif.template import Template, TemplateLibrary

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures/templates"
BLDG = Namespace("urn:bldg#")
more_ns = {"bldg": str(BLDG)}

pytest.skip("old template implementation", allow_module_level=True)


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
        {"name": BLDG["temp-sensor-1"]}, more_namespaces=more_ns
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
            "zone": BLDG["zone1"],
            "sen": BLDG["temp-sensor-1"],
            "name": BLDG["temp-sensor-1"],
        },
        more_namespaces=more_ns,
    )
    assert isinstance(result, Graph)
    assert len(result) == 4


def test_template_fillin_no_deps():
    lib = TemplateLibrary(FIXTURES_DIR / "2.yml")
    temp_sensor_template = lib["temp-sensor"][0]
    assert temp_sensor_template.parameters == {"name"}
    _, result = temp_sensor_template.fill_in(BLDG)
    assert isinstance(result, Graph)
    assert len(result) == 1


def test_template_fillin_with_deps():
    lib = TemplateLibrary(FIXTURES_DIR / "2.yml")
    vav_template = lib["vav"][0]
    vav_template.inline_dependencies()
    assert vav_template.parameters == {"name", "zone", "sen"}
    _, result = vav_template.fill_in(BLDG)
    assert isinstance(result, Graph)
    assert len(result) == 4


def test_partial_template_no_deps():
    lib = TemplateLibrary(FIXTURES_DIR / "2.yml")
    temp_sensor_template = lib["temp-sensor"][0]
    assert temp_sensor_template.parameters == {"name"}
    result = temp_sensor_template.evaluate({}, more_namespaces=more_ns)
    assert isinstance(result, Template)
    assert result.parameters == {"name"}


def test_partial_template_with_deps():
    lib = TemplateLibrary(FIXTURES_DIR / "2.yml")
    vav_template = lib["vav"][0]
    vav_template.inline_dependencies()
    assert vav_template.parameters == {"name", "zone", "sen"}
    result = vav_template.evaluate({"name": BLDG["vav1"]}, more_namespaces=more_ns)
    assert isinstance(result, Template)
    assert result.parameters == {"zone", "sen"}
