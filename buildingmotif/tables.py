from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DBModel(Base):
    """Model containing all building infomation"""

    __tablename__ = "models"
    id = Column(Integer, primary_key=True)
    name = Column(String())
    graph_id = Column(String())
