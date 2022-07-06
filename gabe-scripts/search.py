from rdflib import Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model

BLDG = Namespace("urn:my-building/")

bm = BuildingMOTIF("sqlite://")
bldg = Model.create(str(BLDG))

brick = Library.load(ontology_graph="tests/unit/fixtures/Brick.ttl")
app_shapes = Library.load(directory="tests/unit/fixtures/search")
templ_lib = Library.load(directory="libraries/ashrae/guideline36")
print(app_shapes.get_shape_collection().graph.serialize())

for templ in templ_lib.get_templates():
    print(templ.body.serialize())
