from typing import Dict, List

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, declarative_base, relationship

# from sqlalchemy.dialects.postgresql import JSON
from buildingmotif.database.utils import JSONType

Base = declarative_base()


# https://docs.sqlalchemy.org/en/14/dialects/sqlite.html#foreign-key-support
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

class DBModel(Base):
    """A Model is a metadata model of all or part of a building."""

    __tablename__ = "models"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String())
    description: Mapped[str] = Column(Text(), default="", nullable=False)
    graph_id: Mapped[str] = Column(String())
    manifest_id: Mapped[int] = Column(
        Integer, ForeignKey("shape_collection.id", ondelete="CASCADE"), nullable=False
    )
    manifest: "DBShapeCollection" = relationship(
        "DBShapeCollection",
        uselist=False,
        cascade="all,delete",
        passive_deletes=False,
    )


class DBShapeCollection(Base):
    """A ShapeCollection is a collection of shapes, which are used to validate
    parts of a model.
    """

    __tablename__ = "shape_collection"
    id: Mapped[int] = Column(Integer, primary_key=True)
    graph_id: Mapped[str] = Column(String())


class DBLibrary(Base):
    """A Library is a distributable collection of Templates and Shapes."""

    __tablename__ = "library"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(), nullable=False, unique=True)

    templates: Mapped[List["DBTemplate"]] = relationship(
        "DBTemplate", back_populates="library", cascade="all,delete", passive_deletes=False
    )

    shape_collection_id = Column(
        Integer, ForeignKey("shape_collection.id", ondelete="CASCADE"), nullable=False
    )
    shape_collection: DBShapeCollection = relationship(
        "DBShapeCollection",
        uselist=False,
        cascade="all,delete",
        passive_deletes=False,
    )


class DepsAssociation(Base):
    """Many-to-many relationship between dependant templates."""

    __tablename__ = "deps_association_table"

    id: Mapped[int] = Column(Integer, primary_key=True)
    dependant_id: Mapped[int] = Column(ForeignKey("template.id", ondelete="CASCADE"))
    dependee_id: Mapped[int] = Column(ForeignKey("template.id", ondelete="CASCADE"))
    # args are a mapping of dependee args to dependant args
    args: Mapped[Dict[str, str]] = Column(JSONType)  # type: ignore

    __table_args__ = (
        UniqueConstraint(
            "dependant_id",
            "dependee_id",
            "args",
            name="deps_association_unique_constraint",
        ),
    )


class DBTemplate(Base):
    """A Template is used to generate content for a model."""

    # TODO: doc table properties better.
    __tablename__ = "template"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(), nullable=False)
    body_id: Mapped[str] = Column(String())
    optional_args: Mapped[List[str]] = Column(JSONType)  # type: ignore

    library_id: Mapped[int] = Column(Integer, ForeignKey("library.id", ondelete="CASCADE"), nullable=False)
    library: Mapped[DBLibrary] = relationship("DBLibrary", back_populates="templates")
    dependencies: Mapped[List["DBTemplate"]] = relationship(
        "DBTemplate",
        secondary="deps_association_table",
        primaryjoin=id == DepsAssociation.dependant_id,
        secondaryjoin=id == DepsAssociation.dependee_id,
        back_populates="dependants",
        cascade="all,delete",
        passive_deletes=False,
    )
    dependants: Mapped[List["DBTemplate"]] = relationship(
        "DBTemplate",
        secondary="deps_association_table",
        primaryjoin=id == DepsAssociation.dependee_id,
        secondaryjoin=id == DepsAssociation.dependant_id,
        back_populates="dependencies",
        cascade="all,delete",
        passive_deletes=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "name",
            "library_id",
            name="name_library_unique_constraint",
        ),
    )
