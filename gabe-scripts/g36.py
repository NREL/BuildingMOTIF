from rdflib import Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model

NUM_VAVs = 3
BLDG = Namespace("urn:my-building/")

bm = BuildingMOTIF("sqlite://")
bldg = Model.create("my-building")
lib = Library.load(directory="libraries/g36")
vav_templ = lib.get_template_by_name("vav-cooling-only")

for vav in range(NUM_VAVs):
    vav_name = BLDG[f"vav-{vav}"]
    _, vav_graph = vav_templ.evaluate({"name": vav_name}).fill(BLDG)
    bldg.add_graph(vav_graph)
print(bldg.graph.serialize(format="turtle"))
