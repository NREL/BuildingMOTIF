from rdflib import Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import BRICK, RDF

BLDG = Namespace("urn:my-building/")

bm = BuildingMOTIF("sqlite:///")
bldg = Model.create("my-building")

brick = Library.load(ontology_graph="libraries/brick/Brick-subset.ttl")
site = Library.load(directory="libraries/medium-office")

print(bldg.graph.serialize())

bldg.validate([site.get_shape_collection()])

bldg.graph.add((BLDG["vav1"], RDF.type, BRICK.VAV))

bldg.validate([site.get_shape_collection()])
