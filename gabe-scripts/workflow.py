from rdflib import Graph

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model

bm = BuildingMOTIF("sqlite:///")

brick = Library.load(ontology_graph="tests/unit/fixtures/matching/matching_brick.ttl")
print(brick.name)
lib = Library.load(directory="tests/unit/fixtures/templates")
damper = lib.get_template_by_name("outside-air-damper")

bldg = Model.create("my-building")
bldg.add_graph(Graph().parse("tests/unit/fixtures/matching/matching.ttl"))

for mapping, g, remaining in damper.find_subgraphs(
    bldg, brick.get_shape_collection().graph
):
    print(g.serialize(format="turtle"))
    if remaining:
        print(remaining.body.serialize())
