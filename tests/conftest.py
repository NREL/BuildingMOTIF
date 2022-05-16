from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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
        """
        close session and engine.
        """
        self.session.close()
        self.engine.dispose()
