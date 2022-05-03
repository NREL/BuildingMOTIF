import pytest
from rdflib import Literal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from buildingmotif.db_connections.table_connection import TableConnection


@pytest.fixture
def table_connection(tmpdir, request):
    temp_db_path = tmpdir / f"{request}.db"
    uri = Literal(f"sqlite:///{temp_db_path}")
    engine = create_engine(uri, echo=True)

    class MockBuildingMotif:
        def __init__(self):
            self.engine = engine
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    table_connection = TableConnection(engine, MockBuildingMotif())

    yield table_connection

    table_connection.bm.session.commit()
