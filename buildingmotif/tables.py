from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, declarative_base

Base = declarative_base()


class DBModel(Base):
    """Model containing all building information."""

    __tablename__ = "models"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name = Column(String())
    graph_id = Column(String())
