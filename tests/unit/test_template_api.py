from rdflib import Graph, Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Template
from buildingmotif.namespaces import BRICK, PARAM, A
from buildingmotif.utils import graph_size

BLDG = Namespace("urn:building/")


def test_template_evaluate(bm: BuildingMOTIF):
    """
    Test the Template.evaluate() method.
    """
    lib = Library.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"name", "cav"}

    partial = zone.evaluate({"name": BLDG["zone1"]})
    assert isinstance(partial, Template)
    assert partial.parameters == {"cav"}

    graph = partial.evaluate({"cav": BLDG["cav1"]})
    assert isinstance(graph, Graph)
    assert (BLDG["cav1"], A, BRICK.CAV) in graph
    assert (BLDG["zone1"], A, BRICK.HVAC_Zone) in graph
    assert (BLDG["zone1"], BRICK.isFedBy, BLDG["cav1"]) in graph
    assert len(list(graph.triples((None, None, None)))) == 3


def test_template_fill(bm: BuildingMOTIF):
    """
    Test the Template.fill() method.
    """
    lib = Library.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"name", "cav"}

    bindings, graph = zone.fill(BLDG)
    assert isinstance(bindings, dict)
    assert "name" in bindings.keys()
    assert "cav" in bindings.keys()
    assert isinstance(graph, Graph)
    assert len(list(graph.triples((None, None, None)))) == 3


def test_template_copy(bm: BuildingMOTIF):
    """
    Test the Template.copy() method.
    """
    lib = Library.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"name", "cav"}

    zone2 = zone.in_memory_copy()
    assert zone2.parameters == {"name", "cav"}
    # should be able to edit the copy without editing the original
    zone2.body.add((PARAM["zone2"], A, BRICK.Zone))
    assert zone2.parameters == {"name", "zone2", "cav"}
    assert zone.parameters == {"name", "cav"}


def test_template_to_inline(bm: BuildingMOTIF):
    """
    Test the Template.to_inline() method.
    """
    lib = Library.load(directory="tests/unit/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"name", "cav"}

    # inline *all* parameters
    inlined = zone.to_inline()
    assert all([x.endswith("-inlined") for x in inlined.parameters])
    assert len(inlined.parameters) == len(zone.parameters)

    # inline *some* parameters
    inlined = zone.to_inline(preserve_args=["cav"])
    inlined_params = [
        x for x in inlined.parameters if x.endswith("-inlined") and x.startswith("name")
    ]
    assert len(inlined_params) == 1
    assert "cav" in inlined.parameters


def test_template_inline_dependencies(bm: BuildingMOTIF):
    """
    Test the Template.inline_dependencies() method.
    """
    lib = Library.load(directory="tests/unit/fixtures/templates")
    templ = lib.get_template_by_name("single-zone-vav-ahu")
    assert len(templ.get_dependencies()) == 2
    inlined = templ.inline_dependencies()
    assert len(inlined.get_dependencies()) == 0
    preserved_params = {
        "name",
        "sf",
        "oad",
        "cd",
        "hd",
        "zt",
        "occ",
        "mat",
        "rat",
        "sat",
        "oat",
        "zone",
        "spd",
        "ss",
        "st",
        "pos",
    }
    assert inlined.parameters == preserved_params


def test_template_evaluate_with_optional(bm: BuildingMOTIF):
    """
    Test that template evaluation works with optional parameters.
    """
    lib = Library.load(directory="tests/unit/fixtures/templates")
    templ = lib.get_template_by_name("opt-vav")
    assert templ.parameters == {"name", "occ", "zone"}
    assert templ.optional_args == ["occ"]
    g = templ.evaluate({"name": BLDG["vav"], "zone": BLDG["zone1"]})
    assert isinstance(g, Graph)
    assert graph_size(g) == 1

    t = templ.evaluate(
        {"name": BLDG["vav"], "zone": BLDG["zone1"]}, require_optional_args=True
    )
    assert isinstance(t, Template)
    assert t.parameters == {"occ"}
