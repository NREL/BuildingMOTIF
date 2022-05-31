from rdflib import Graph, Namespace

from buildingmotif.building_motif import BuildingMotif
from buildingmotif.dataclasses.template import Template
from buildingmotif.namespaces import BRICK, A

BLDG = Namespace("urn:building/")


def test_template_evaluate(bm: BuildingMotif):
    """
    Test the Template.evaluate() method.
    """
    lib = bm.load_library(directory="tests/fixtures/templates")
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


def test_template_fill(bm: BuildingMotif):
    """
    Test the Template.evaluate() method.
    """
    lib = bm.load_library(directory="tests/fixtures/templates")
    zone = lib.get_template_by_name("zone")
    assert zone.parameters == {"zone", "cav"}
    assert sorted(zone.head) == sorted(("zone", "cav"))

    bindings, graph = zone.fill(BLDG)
    assert isinstance(bindings, dict)
    assert "zone" in bindings.keys()
    assert "cav" in bindings.keys()
    assert isinstance(graph, Graph)
    assert len(list(graph.triples((None, None, None)))) == 3
