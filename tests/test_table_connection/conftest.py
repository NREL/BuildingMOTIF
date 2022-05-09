import pytest
from rdflib import Literal

from buildingmotif.db_connections.table_connection import TableConnection
from tests.conftest import MockBuildingMotif


@pytest.fixture
def table_connection(tmpdir, request):
    temp_db_path = tmpdir / f"{request}.db"
    uri = Literal(f"sqlite:///{temp_db_path}")
    bm = MockBuildingMotif(uri)

    yield TableConnection(bm.engine, bm)

    bm.session.commit()
    bm.release()
