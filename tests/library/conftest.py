import os

import pytest
from pytest import MonkeyPatch

import buildingmotif.building_motif.building_motif
import buildingmotif.building_motif.singleton

# The fact that BuildingMOTIF is a singleton class is a problem for testing templates.
# We want to have tests which are parameterized by the library and template name; this makes
# it possible to use pytest filters (with the "-k" flag) to run tests for specific libraries or templates.
# We want each (library, template) pair to operate in a "clean" environment, so that the tests are isolated.
# However, the singleton pattern means that the BuildingMOTIF instance is shared across all tests.
# We can work around this by patching BuildingMOTIF to ignore the singleton pattern.


# we need to set up monkey patching in two places. Inside the "conftest.py" file (here) and within each test file,
# which we do within the "autouse" pytest.fixture.
mp = MonkeyPatch()
# "instances" is a dictionary that maps the name of the module to the BuildingMOTIF instance.
instances = {}


# The normal get_building_motif method uses the fact that BuildingMOTIF is a singleton class.
# We need to mock this method so that we can create a new instance of BuildingMOTIF for each test.
# We use the "instances" dictionary to store the BuildingMOTIF instance for each module.
# If the instance does not exist, we create a new one and store it in the dictionary.
# TODO: how to handle testing different shacl_engines?
def mock_building_motif():
    from buildingmotif import BuildingMOTIF

    name = os.environ["bmotif_module"]
    if name not in instances:
        instances[name] = BuildingMOTIF("sqlite://", shacl_engine="topquadrant")
        instances[name].setup_tables()
    return instances[name]


# We need to patch the BuildingMOTIF class to ignore the singleton pattern when configuring the tests

# this patches the behavior of the Singleton class to use "type" (the default Python metaclass) instead of the singleton pattern.
# we patch the Singleton class in the building_motif module and the building_motif module itself.
mp.setattr(buildingmotif.building_motif.singleton, "Singleton", type)
mp.setattr(buildingmotif.building_motif.building_motif, "Singleton", type)
# we patch the get_building_motif method in the building_motif module and the buildingmotif module.
# this uses the mock_building_motif method we defined above.
mp.setattr(
    buildingmotif.building_motif.building_motif,
    "get_building_motif",
    mock_building_motif,
)
mp.setattr(buildingmotif, "get_building_motif", mock_building_motif)


# this fixture is automatically applied to all tests. It monkeypatches the building motif module to ignore the singleton pattern.
@pytest.fixture(autouse=True)
def patch_bmotif(monkeypatch):
    monkeypatch.setattr(buildingmotif.building_motif.singleton, "Singleton", type)
    monkeypatch.setattr(buildingmotif.building_motif.building_motif, "Singleton", type)
    monkeypatch.setattr(
        buildingmotif.building_motif.building_motif,
        "get_building_motif",
        mock_building_motif,
    )
    monkeypatch.setattr(buildingmotif, "get_building_motif", mock_building_motif)
