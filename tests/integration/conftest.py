"""
Generates tests automatically
"""
import pytest

from buildingmotif import BuildingMOTIF


@pytest.fixture
def bm():
    """
    BuildingMotif instance for tests involving dataclasses and API calls
    """
    bm = BuildingMOTIF("sqlite://")
    # add tables to db
    bm.setup_tables()

    yield bm
    bm.close()
    # clean up the singleton so that tables are re-created correctly later
    BuildingMOTIF.clean()
