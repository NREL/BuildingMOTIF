import pytest

from buildingmotif.db_connections.table_connection import TableConnection
from tests.conftest import MockBuildingMotif


@pytest.fixture
def table_connection():
    bm = MockBuildingMotif()

    yield TableConnection(bm.engine, bm)

    bm.session.commit()
    bm.close()
