import os
import tempfile

import pytest

from building_motif import BuildingMOTIF


@pytest.fixture
def clean_building_motif():
    BuildingMOTIF.clean()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_db_path = os.path.join(tempdir, "temp.db")
        uri = f"sqlite:///{temp_db_path}"
        building_motif = BuildingMOTIF(uri)

        yield building_motif

        building_motif.session.commit()
        building_motif.close()
        BuildingMOTIF.clean()
