import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from buildingmotif import BuildingMOTIF


class MockBuildingMotif:
    """BuildingMOTIF for testing connections.

    Not a singletion, no connections classes, just the engine and connection. So
    we can pass this to the connections.
    """

    def __init__(self) -> None:
        """Class constructor."""
        self.engine = create_engine("sqlite://", echo=False)
        Session = sessionmaker(bind=self.engine, autoflush=True)
        self.session = Session()

    def close(self) -> None:
        """Close session and engine."""
        self.session.close()
        self.engine.dispose()


@pytest.fixture
def bm():
    """
    BuildingMotif instance for tests involving dataclasses and API calls
    """
    bm = BuildingMOTIF("sqlite://")
    yield bm
    bm.close()
    # clean up the singleton so that tables are re-created correctly later
    BuildingMOTIF.clean()
