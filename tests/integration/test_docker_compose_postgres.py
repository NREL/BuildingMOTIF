import shlex
import subprocess
from pathlib import Path

import pytest

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library

# path to libraries
libraries_path = Path(__file__).parent.parent.parent / Path("libraries")
# path to docker compose file (in root of repo)
docker_compose_path = Path(__file__).parent / Path("fixtures") / Path("pgtest")
# clean up docker compose
docker_compose_clean = shlex.split("docker compose rm -fsv")
# command to start docker compose
docker_compose_start = shlex.split("docker compose up -d --build")
# command to stop docker compose
docker_compose_stop = shlex.split("docker compose down")


@pytest.fixture()
def docker_compose_setup():
    subprocess.run(docker_compose_clean, cwd=docker_compose_path)
    subprocess.run(docker_compose_start, cwd=docker_compose_path)
    yield
    subprocess.run(docker_compose_stop, cwd=docker_compose_path)


@pytest.fixture
def bm_pg():
    """
    BuildingMotif instance for tests involving dataclasses and API calls
    Uses Postgres connection defined in the .env file!
    """
    db_uri = "postgresql://bmotif_pgtest:password@localhost:5432/bmotif_pgtest"
    bm = BuildingMOTIF(db_uri)
    # don't need to add tables to db; this is already done for us by the container

    yield bm
    bm.close()
    # clean up the singleton so that tables are re-created correctly later
    BuildingMOTIF.clean()


@pytest.mark.integration
def test_load_libraries(docker_compose_setup, bm_pg):
    """
    Tests that libraries load correctly into BuildingMOTIF
    """
    Library.load(ontology_graph=str(libraries_path / "brick" / "Brick-full.ttl"))
    Library.load(directory=str(libraries_path / "ashrae" / "guideline36"))
    bm_pg.session.commit()
