import pytest
import testing.postgresql

from buildingmotif import BuildingMOTIF
from buildingmotif.api.app import create_app


@pytest.fixture
def building_motif():
    BuildingMOTIF.clean()
    with testing.postgresql.Postgresql() as postgresql:
        building_motif = BuildingMOTIF(postgresql.url())
        # add tables to db
        building_motif.setup_tables()

        yield building_motif

        building_motif.session.commit()
        building_motif.close()
        BuildingMOTIF.clean()


@pytest.fixture
def app(building_motif):
    app = create_app(DB_URI=building_motif.db_uri)
    app.config["TESTING"] = True

    return app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client
