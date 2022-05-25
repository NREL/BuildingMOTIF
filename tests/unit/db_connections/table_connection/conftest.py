import pytest

from building_motif.database.table_connection import TableConnection
from tests.unit.conftest import MockBuildingMotif


@pytest.fixture
def table_connection():
    bm = MockBuildingMotif()

    yield TableConnection(bm.engine, bm)

    bm.session.commit()
    bm.close()
