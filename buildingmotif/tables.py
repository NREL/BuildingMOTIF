from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
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

    templates: Mapped[list["DBTemplate"]] = relationship(
        "DBTemplate", back_populates="template_library", cascade="all,delete"
    )


class DBTemplate(Base):
    """Template"""

    __tablename__ = "template"
    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(), nullable=False)
    body_id: Mapped[str] = Column(String())

    template_library_id = Column(
        Integer, ForeignKey("template_library.id"), nullable=False
    )
    template_library: DBTemplateLibrary = relationship(
        "DBTemplateLibrary", back_populates="templates"
    )

    __table_args__ = (
        UniqueConstraint(
            "name",
            "template_library_id",
            name="name_template_library_unique_constraint",
        ),
    )
