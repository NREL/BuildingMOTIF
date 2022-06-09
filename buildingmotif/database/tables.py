from typing import Dict, List, Tuple

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, declarative_base, relationship

Base = declarative_base()


class DBModel(Base):
    """Model containing all building information."""

    __tablename__ = "models"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String())
    graph_id: Mapped[str] = Column(String())


class DBTemplateLibrary(Base):
    """Collection of Templates"""

    __tablename__ = "template_library"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(), nullable=False, unique=True)

    templates: Mapped[List["DBTemplate"]] = relationship(
        "DBTemplate", back_populates="template_library", cascade="all,delete"
    )


class DepsAssociation(Base):
    """Many-to-many relationship between dependant templates."""

    __tablename__ = "deps_association_table"

    dependant_id: Mapped[int] = Column(ForeignKey("template.id"), primary_key=True)
    dependee_id: Mapped[int] = Column(ForeignKey("template.id"), primary_key=True)
    # args are a mapping of dependee args to dependant args
    args: Mapped[Dict[str, str]] = Column(JSON)


class DBTemplate(Base):
    """Template.

    # TODO: doc table properties better.
    """

    __tablename__ = "template"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(), nullable=False)
    _head: Mapped[str] = Column(String(), nullable=False)
    body_id: Mapped[str] = Column(String())
    optional_args: Mapped[List[str]] = Column(JSON)

    template_library_id = Column(
        Integer, ForeignKey("template_library.id"), nullable=False
    )
    template_library: DBTemplateLibrary = relationship(
        "DBTemplateLibrary", back_populates="templates"
    )
    dependencies: Mapped["DBTemplate"] = relationship(
        "DBTemplate",
        secondary="deps_association_table",
        primaryjoin=id == DepsAssociation.dependant_id,
        secondaryjoin=id == DepsAssociation.dependee_id,
        back_populates="dependants",
    )
    dependants: Mapped["DBTemplate"] = relationship(
        "DBTemplate",
        secondary="deps_association_table",
        primaryjoin=id == DepsAssociation.dependee_id,
        secondaryjoin=id == DepsAssociation.dependant_id,
        back_populates="dependencies",
    )

    __table_args__ = (
        UniqueConstraint(
            "name",
            "template_library_id",
            name="name_template_library_unique_constraint",
        ),
    )

    @hybrid_property
    def head(self) -> Tuple[str, ...]:
        return tuple([x for x in self._head.split(";")])
