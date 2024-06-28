import os

import pytest
from pytest import MonkeyPatch

import buildingmotif
import buildingmotif.building_motif.building_motif
import buildingmotif.building_motif.singleton
from buildingmotif.dataclasses import Library

# The fact that BuildingMOTIF is a singleton class is a problem for testing templates.
# We want to have tests which are parameterized by the library and template name; this makes
# it possible to use pytest filters (with the "-k" flag) to run tests for specific libraries or templates.
# We want each (library, template) pair to operate in a "clean" environment, so that the tests are isolated.
# However, the singleton pattern means that the BuildingMOTIF instance is shared across all tests.
# We can work around this by patching BuildingMOTIF to ignore the singleton pattern.

# "instances" is a dictionary that maps the name of the module to the BuildingMOTIF instance.
instances = {}
old_get_building_motif = buildingmotif.building_motif.building_motif.get_building_motif
old_singleton = buildingmotif.building_motif.singleton.Singleton


# The normal get_building_motif method uses the fact that BuildingMOTIF is a singleton class.
# We need to mock this method so that we can create a new instance of BuildingMOTIF for each test.
# We use the "instances" dictionary to store the BuildingMOTIF instance for each module.
# If the instance does not exist, we create a new one and store it in the dictionary.
# TODO: how to handle testing different shacl_engines?
def mock_building_motif():
    global instances
    from buildingmotif import BuildingMOTIF

    name = os.environ["bmotif_module"]
    if name not in instances:
        instances[name] = BuildingMOTIF("sqlite://", shacl_engine="topquadrant")
        instances[name].setup_tables()
    return instances[name]


# this fixture is automatically applied to all tests. It monkeypatches the building motif module to ignore the singleton pattern.
@pytest.fixture(autouse=True, scope="function")
def patch_bmotif(monkeypatch):
    monkeypatch.setattr(buildingmotif.building_motif.singleton, "Singleton", type)
    monkeypatch.setattr(buildingmotif.building_motif.building_motif, "Singleton", type)
    monkeypatch.setattr(
        buildingmotif.building_motif.building_motif,
        "get_building_motif",
        mock_building_motif,
    )
    monkeypatch.setattr(buildingmotif, "get_building_motif", mock_building_motif)


def library_load(**kwargs):
    with MonkeyPatch().context() as m:
        m.setattr(
            buildingmotif.dataclasses.library, "get_building_motif", mock_building_motif
        )
        m.setattr(
            buildingmotif.dataclasses.model, "get_building_motif", mock_building_motif
        )
        m.setattr(
            buildingmotif.dataclasses.shape_collection,
            "get_building_motif",
            mock_building_motif,
        )
        m.setattr(
            buildingmotif.dataclasses.template,
            "get_building_motif",
            mock_building_motif,
        )
        return Library.load(**kwargs)


#  create a contextmanager that patches the building motif module to ignore the singleton pattern.


class PatchBuildingMotif:
    def __enter__(self):
        print("patching")
        self.monkeypatch = MonkeyPatch()
        self.monkeypatch.setattr(
            buildingmotif.dataclasses.library, "get_building_motif", mock_building_motif
        )
        self.monkeypatch.setattr(
            buildingmotif.dataclasses.model, "get_building_motif", mock_building_motif
        )
        self.monkeypatch.setattr(
            buildingmotif.dataclasses.shape_collection,
            "get_building_motif",
            mock_building_motif,
        )
        self.monkeypatch.setattr(
            buildingmotif.dataclasses.template,
            "get_building_motif",
            mock_building_motif,
        )
        return self.monkeypatch

    def __exit__(self, *args):
        print("undoing patch")
        self.monkeypatch.undo()
