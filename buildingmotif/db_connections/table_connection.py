import uuid
from functools import wraps
from typing import Callable, List, Optional

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from buildingmotif.tables import Base, DBModel, DBTemplate, DBTemplateLibrary


def _commit_or_rollback(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return res

    return wrapper


class TableConnection:
    """Controls interaction with the database."""

    def __init__(self, engine: Engine) -> None:
        """Class constructor.

        :param engine: db engine
        :type engine: Engine
        """
        # create tables
        Base.metadata.create_all(engine)

        # create session
        Session = sessionmaker(bind=engine)
        self.session = Session()

    # model functions

    @_commit_or_rollback
    def create_db_model(self, name: str) -> DBModel:
        """Create a database model.

        :param name: name of dbmodel
        :type name: str
        :return: DBModel
        :rtype: DBModel
        """
        db_model = DBModel(name=name, graph_id=str(uuid.uuid4()))

        self.session.add(db_model)

        return db_model

    def get_all_db_models(self) -> List[DBModel]:
        """Get all database models.

        :return: all DBModels
        :rtype: DBModel
        """
        return self.session.query(DBModel).all()

    def get_db_model(self, id: int) -> DBModel:
        """Get database model from id.

        :param id: id of DBModel
        :type id: str
        :return: DBModel
        :rtype: DBModel
        """
        return self.session.query(DBModel).filter(DBModel.id == id).one()

    @_commit_or_rollback
    def update_db_model_name(self, id: int, name: Optional[str]) -> None:
        """Update database model.

        :param id: id of DBModel
        :type id: str
        :param name: new name
        :type name: str
        """
        db_model = self.session.query(DBModel).filter(DBModel.id == id).one()
        db_model.name = name

    @_commit_or_rollback
    def delete_db_model(self, id: int) -> None:
        """Delete database model.

        :param id: id of deleted DBModel
        :type id: str
        """
        db_model = self.session.query(DBModel).filter(DBModel.id == id).one()

        self.session.delete(db_model)

    # template library functions

    @_commit_or_rollback
    def create_db_template_library(self, name: str) -> DBTemplateLibrary:
        """Create a database template_library.

        :param name: name of DBTemplateLibrary
        :type name: str
        :return: DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        template_library = DBTemplateLibrary(name=name)

        self.session.add(template_library)

        return template_library

    def get_all_db_template_libraries(self) -> List[DBTemplateLibrary]:
        """Get all database template library.

        :return: all DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        return self.session.query(DBTemplateLibrary).all()

    def get_db_template_library(self, id: int) -> DBTemplateLibrary:
        """Get database template library from id.

        :param id: id of DBTemplateLibrary
        :type id: str
        :return: DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        return (
            self.session.query(DBTemplateLibrary)
            .filter(DBTemplateLibrary.id == id)
            .one()
        )

    @_commit_or_rollback
    def update_db_template_library_name(self, id: int, name: Optional[str]) -> None:
        """Update database template library.

        :param id: id of DBTemplateLibrary
        :type id: str
        :param name: new name
        :type name: str
        """
        db_template_library = (
            self.session.query(DBTemplateLibrary)
            .filter(DBTemplateLibrary.id == id)
            .one()
        )
        db_template_library.name = name

    @_commit_or_rollback
    def delete_db_template_library(self, id: int) -> None:
        """Delete database template library.

        :param id: id of deleted DBTemplateLibrary
        :type id: str
        """
        db_template_library = (
            self.session.query(DBTemplateLibrary)
            .filter(DBTemplateLibrary.id == id)
            .one()
        )

        self.session.delete(db_template_library)

    # template functions

    @_commit_or_rollback
    def create_db_template(self, name: str, template_library_id: int) -> DBTemplate:
        """Create a database template.

        :param name: name of DBTemplate
        :type name: str
        :param template_library_id: id of the template's library
        :return: DBTemplate
        :rtype: DBTemplate
        """
        template_library = self.get_db_template_library(template_library_id)
        template = DBTemplate(
            name=name, body_id=str(uuid.uuid4()), template_library=template_library
        )

        return template

    def get_all_db_templates(self) -> List[DBTemplate]:
        """Get all database template.

        :return: all DBTemplate
        :rtype: DBTemplate
        """
        return self.session.query(DBTemplate).all()

    def get_db_template(self, id: int) -> DBTemplate:
        """Get database template from id.

        :param id: id of DBTemplate
        :type id: str
        :return: DBTemplate
        :rtype: DBTemplate
        """
        return self.session.query(DBTemplate).filter(DBTemplate.id == id).one()

    @_commit_or_rollback
    def update_db_template_name(self, id: int, name: Optional[str]) -> None:
        """Update database template.

        :param id: id of DBTemplate
        :type id: str
        :param name: new name
        :type name: str
        """
        db_template = self.session.query(DBTemplate).filter(DBTemplate.id == id).one()
        db_template.name = name

    @_commit_or_rollback
    def update_db_template_template_library(
        self, id: int, template_library_id: int
    ) -> None:
        """Update database template.

        :param id: id of DBTemplate
        :type id: str
        :param name: id of the new template_library
        :type name: int
        """
        db_template = self.session.query(DBTemplate).filter(DBTemplate.id == id).one()
        db_template.template_library = template_library_id

    @_commit_or_rollback
    def delete_db_template(self, id: int) -> None:
        """Delete database template.

        :param id: id of deleted DBTemplate
        :type id: str
        """
        db_template = self.session.query(DBTemplate).filter(DBTemplate.id == id).one()

        self.session.delete(db_template)
