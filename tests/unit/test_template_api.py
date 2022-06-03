from rdflib import Graph, Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Template, TemplateLibrary
from buildingmotif.namespaces import BRICK, A

BLDG = Namespace("urn:building/")


def test_template_evaluate(bm: BuildingMOTIF):
    """
    Test the Template.evaluate() method.
    """
    lib = TemplateLibrary.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"zone", "cav"}
    assert sorted(zone.head) == sorted(("zone", "cav"))

    partial = zone.evaluate({"zone": BLDG["zone1"]})
    assert isinstance(partial, Template)
    assert partial.parameters == {"cav"}
    assert partial.head == ("cav",)

    graph = partial.evaluate({"cav": BLDG["cav1"]})
    assert isinstance(graph, Graph)
    assert (BLDG["cav1"], A, BRICK.CAV) in graph
    assert (BLDG["zone1"], A, BRICK.HVAC_Zone) in graph
    assert (BLDG["zone1"], BRICK.isFedBy, BLDG["cav1"]) in graph
    assert len(list(graph.triples((None, None, None)))) == 3


def test_template_fill(bm: BuildingMOTIF):
    """
    Test the Template.evaluate() method.
    """
    lib = TemplateLibrary.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"zone", "cav"}
    assert sorted(zone.head) == sorted(("zone", "cav"))

    bindings, graph = zone.fill(BLDG)
    assert isinstance(bindings, dict)
    assert "zone" in bindings.keys()
    assert "cav" in bindings.keys()
    assert isinstance(graph, Graph)
    assert len(list(graph.triples((None, None, None)))) == 3


def test_template_copy(bm: BuildingMOTIF):
    """
    Test the Template.copy() method.
    """
    lib = TemplateLibrary.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"zone", "cav"}
    assert sorted(zone.head) == sorted(("zone", "cav"))

    zone2 = zone.in_memory_copy()
    assert zone2.parameters == {"zone", "cav"}
    assert sorted(zone2.head) == sorted(("zone", "cav"))
    # should be able to edit the copy without editing the original
    zone2._head = ("a", "b")
    assert sorted(zone2.head) == sorted(("a", "b"))
    assert zone.parameters == {"zone", "cav"}
    assert sorted(zone.head) == sorted(("zone", "cav"))


def test_template_to_inline(bm: BuildingMOTIF):
    """
    Test the Template.to_inline() method
    """
    lib = TemplateLibrary.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"zone", "cav"}

    # inline *all* parameters
    inlined = zone.to_inline()
    assert all([x.endswith("-inlined") for x in inlined.parameters])
    assert len(inlined.parameters) == len(zone.parameters)

    # inline *some* parameters
    inlined = zone.to_inline(preserve_args=["zone"])
    inlined_params = [
        x for x in inlined.parameters if x.endswith("-inlined") and x.startswith("cav")
    ]
    assert len(inlined_params) == 1
    assert "zone" in inlined.parameters


def test_template_inline_dependencies(bm: BuildingMOTIF):
    """
    Test the Template.inline_dependencies() method
    """
    lib = TemplateLibrary.load(directory="tests/unit/fixtures/templates")
    templ = lib.get_template_by_name("single-zone-vav-ahu")
    assert len(templ.get_dependencies()) == 2
    inlined = templ.inline_dependencies()
    assert len(inlined.get_dependencies()) == 0
