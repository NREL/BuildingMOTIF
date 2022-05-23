import os
import tempfile

import pytest

from buildingmotif.building_motif.building_motif import BuildingMotif


@pytest.fixture
def clean_building_motif():
    BuildingMotif.clean()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_db_path = os.path.join(tempdir, "temp.db")
        uri = f"sqlite:///{temp_db_path}"
        building_motif = BuildingMotif(uri)

        yield building_motif

        building_motif.session.commit()
        building_motif.close()
        BuildingMotif.clean()
