import os
import tempfile

import pytest

from buildingmotif import BuildingMOTIF
from buildingmotif.api.app import create_app


@pytest.fixture
def building_motif():
    BuildingMOTIF.clean()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_db_path = os.path.join(tempdir, "temp.db")
        uri = f"sqlite:///{temp_db_path}"
        building_motif = BuildingMOTIF(uri)
        # add tables to db
        building_motif.setup_tables()

        yield building_motif

        building_motif.session.commit()
        building_motif.close()
        BuildingMOTIF.clean()


@pytest.fixture
def app(building_motif, shacl_engine):
    app = create_app(DB_URI=building_motif.db_uri, shacl_engine=shacl_engine)
    app.config["TESTING"] = True

    return app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client
