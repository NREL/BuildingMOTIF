from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library

bm = BuildingMOTIF("sqlite://")
Library.load(ontology_graph="libraries/brick/Brick-subset.ttl")
