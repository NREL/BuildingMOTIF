import pytest
import testing.postgresql

from buildingmotif import BuildingMOTIF


@pytest.fixture
def clean_building_motif():
    BuildingMOTIF.clean()
    with testing.postgresql.Postgresql() as postgresql:
        building_motif = BuildingMOTIF(postgresql.url())
        # add tables to db
        building_motif.setup_tables()

        yield building_motif

        building_motif.session.commit()
        building_motif.close()
        BuildingMOTIF.clean()
