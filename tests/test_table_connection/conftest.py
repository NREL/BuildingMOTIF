import pytest
from rdflib import Literal
from sqlalchemy import create_engine

from buildingmotif.db_connections.table_connection import TableConnection


@pytest.fixture
def table_connection(tmpdir, request):
    temp_db_path = tmpdir / f"{request}.db"
    uri = Literal(f"sqlite:///{temp_db_path}")
    engine = create_engine(uri, echo=True)

    return TableConnection(engine)
