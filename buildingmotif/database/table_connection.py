import logging
import uuid
from typing import Dict, List, Tuple

from sqlalchemy.engine import Engine

from buildingmotif.database.tables import (
    Base,
    DBModel,
    DBTemplate,
    DBTemplateLibrary,
    DepsAssociation,
)


class TableConnection:
    """Controls interaction with the database."""

    def __init__(self, engine: Engine, bm) -> None:
        """Class constructor.

        :param engine: db engine
        :type engine: Engine
        :param bm: contains the session to use
        :type bm: BuildingMotif
        """
        # create tables
        self.logger = logging.getLogger(__name__)

        self.logger.debug("Creating tables for data storage")
        Base.metadata.create_all(engine)
        self.bm = bm

    # model functions

    def create_db_model(self, name: str) -> DBModel:
        """Create a database model.

        :param name: name of dbmodel
        :type name: str
        :return: DBModel
        :rtype: DBModel
        """
        graph_id = str(uuid.uuid4())
        self.logger.debug(f"Creating model '{name}' with graph '{graph_id}'")
        db_model = DBModel(name=name, graph_id=graph_id)

        self.bm.session.add(db_model)
        self.logger.debug(f"Flushing model '{name}' to database")
        self.bm.session.flush()

        return db_model

    def get_all_db_models(self) -> List[DBModel]:
        """Get all database models.

        :return: all DBModels
        :rtype: DBModel
        """
        return self.bm.session.query(DBModel).all()

    def get_db_model(self, id: int) -> DBModel:
        """Get database model from id.

        :param id: id of DBModel
        :type id: str
        :return: DBModel
        :rtype: DBModel
        """
        self.logger.debug(f"Retrieving model with id '{id}' from database")
        db_model = self.bm.session.query(DBModel).filter(DBModel.id == id).one()
        self.logger.debug(f"Found model with id '{db_model.id}'")
        return db_model

    def update_db_model_name(self, id: int, name: str) -> None:
        """Update database model.

        :param id: id of DBModel
        :type id: str
        :param name: new name
        :type name: str
        """
        db_model = self.get_db_model(id)
        self.logger.debug(f"Updating model name from '{db_model.name}' to '{name}'")
        db_model.name = name

    def delete_db_model(self, id: int) -> None:
        """Delete database model.

        :param id: id of deleted DBModel
        :type id: str
        """

        db_model = self.get_db_model(id)
        self.logger.debug(f"Deleting model '{db_model.name}' from database")
        self.bm.session.delete(db_model)

    # template library functions

    def create_db_template_library(self, name: str) -> DBTemplateLibrary:
        """Create a database template_library.

        :param name: name of DBTemplateLibrary
        :type name: str
        :return: DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        template_library = DBTemplateLibrary(name=name)
        self.logger.debug(f"Creating template library '{name}'")

        self.bm.session.add(template_library)
        self.logger.debug(f"Flushing template library '{name}' to database")
        self.bm.session.flush()

        return template_library

    def get_all_db_template_libraries(self) -> List[DBTemplateLibrary]:
        """Get all database template library.

        :return: all DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        db_template_libraries = self.bm.session.query(DBTemplateLibrary).all()
        self.logger.debug(
            f"Got all template libraries and found '{len(db_template_libraries)}"
        )
        return db_template_libraries

    def get_db_template_library(self, id: int) -> DBTemplateLibrary:
        """Get database template library from id.

        :param id: id of DBTemplateLibrary
        :type id: str
        :return: DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        self.logger.debug(f"Retrieving template library with id '{id}' from database")
        db_template_library = (
            self.bm.session.query(DBTemplateLibrary)
            .filter(DBTemplateLibrary.id == id)
            .one()
        )
        self.logger.debug(f"Found template library with id '{db_template_library.id}'")
        return db_template_library

    def update_db_template_library_name(self, id: int, name: str) -> None:
        """Update database template library.

        :param id: id of DBTemplateLibrary
        :type id: str
        :param name: new name
        :type name: str
        """
        db_template_library = self.get_db_template_library(id)
        self.logger.debug(
            f"Updating template library name from '{db_template_library.name}' to {name}"
        )
        db_template_library.name = name

    def delete_db_template_library(self, id: int) -> None:
        """Delete database template library.

        :param id: id of deleted DBTemplateLibrary
        :type id: str
        """

        db_template_library = self.get_db_template_library(id)

        self.logger.debug(
            f"Deleting template library '{db_template_library.name}' from database"
        )
        self.bm.session.delete(db_template_library)

    # template functions

    def create_db_template(
        self, name: str, head: List[str], template_library_id: int
    ) -> DBTemplate:
        """Create a database template.

        :param name: name of DBTemplate
        :type name: str
        :param name: list of heads
        :type name: list[str]
        :param template_library_id: id of the template's library
        :return: DBTemplate
        :rtype: DBTemplate
        """
        self.logger.debug(f"Creating template '{name}'")
        template_library = self.get_db_template_library(template_library_id)
        template = DBTemplate(
            name=name,
            _head=";".join(head),
            body_id=str(uuid.uuid4()),
            template_library=template_library,
        )

        self.bm.session.add(template)
        self.logger.debug(f"Flushing template '{name}' to database")
        self.bm.session.flush()

        return template

    def get_all_db_templates(self) -> List[DBTemplate]:
        """Get all database template.

        :return: all DBTemplate
        :rtype: DBTemplate
        """
        db_templates = self.bm.session.query(DBTemplate).all()
        self.logger.debug(f"Got all templates and found '{len(db_templates)}")
        return db_templates

    def get_db_template(self, id: int) -> DBTemplate:
        """Get database template from id.

        :param id: id of DBTemplate
        :type id: str
        :return: DBTemplate
        :rtype: DBTemplate
        """
        self.logger.debug(f"Retrieving template with id '{id}' from database")
        db_template = (
            self.bm.session.query(DBTemplate).filter(DBTemplate.id == id).one()
        )
        self.logger.debug(f"Found template with id '{db_template.id}'")
        return db_template

    def get_db_template_by_name(self, name: str) -> DBTemplate:
        """Get database template from id.

        :param name: name of DBTemplate
        :type name: str
        :return: DBTemplate
        :rtype: DBTemplate
        """
        self.logger.debug(f"Retrieving template with name '{name}' from database")
        db_template = (
            self.bm.session.query(DBTemplate).filter(DBTemplate.name == name).one()
        )
        self.logger.debug(f"Found template with name '{db_template.name}'")
        return db_template

    def get_db_template_dependencies(self, id: int) -> Tuple[DepsAssociation, ...]:
        """Get a template's dependencies and its arguments.
        If you don't need the arguments, consider using `template.dependencies`.

        :param id: template id
        :type id: int
        :return: tuple of tuple, where each tuple has 1. the dependant_id, and 2. it's args
        :rtype: tuple[tuple[int, list[str]]]
        """
        self.logger.debug(f"Retrieving dependencies for template with id '{id}'")
        db_template_dependencies = tuple(
            self.bm.session.query(DepsAssociation)
            .filter(DepsAssociation.dependant_id == id)
            .all()
        )
        self.logger.debug(
            f"Found '{len(db_template_dependencies)}' dependencies for template with id '{id}'"
        )
        return db_template_dependencies

    def update_db_template_name(self, id: int, name: str) -> None:
        """Update database template.

        :param id: id of DBTemplate
        :type id: str
        :param name: new name
        :type name: str
        """
        db_template = self.get_db_template(id)
        self.logger.debug(
            f"Updating template library name from '{db_template.name}' to {name}"
        )
        db_template.name = name

    def add_template_dependency(
        self, template_id: int, dependency_id: int, args: Dict[str, str]
    ):
        """Create dependency between two templates.

        :param template_id: dependant template id
        :type template_id: int
        :param dependency_id: dependency template id
        :type dependency_id: int
        :param args: dependency head to dependant variable mapping
        :type args: Dict[str, str]
        :raises ValueError: if all dependee heads not in args
        :raises ValueError: if dependant and dependency template don't share a library
        """
        dependency = self.get_db_template(dependency_id)
        if not all((dependee_arg in args.keys()) for dependee_arg in dependency.head):
            raise ValueError(
                f"All args in dependee template {dependency_id}'s head must be in args ({args})"
            )

        # In the past we had a check here to make sure the two templates were in the same library.
        # This has been removed because it wasn't actually necessary, but we may add it back in
        # in the future.
        self.logger.debug(
            f"Creating depencency from templates with ids '{template_id}' and '{dependency_id}'"
        )
        relationship = DepsAssociation(
            dependant_id=template_id,
            dependee_id=dependency_id,
            args=args,
        )

        self.bm.session.add(relationship)
        self.logger.debug(
            f"Flushing depencency from templates with ids '{template_id}' and '{dependency_id}' to database"  # noqa
        )
        self.bm.session.flush()

    def remove_template_dependency(self, template_id: int, dependency_id: int):
        """Remove dependency between two templates.

        :param template_id: dependant template id
        :type template_id: int
        :param dependency_id: dependency template id
        :type dependency_id: int
        """
        self.logger.debug(
            f"Retrieving depencency from templates with ids '{template_id}' and '{dependency_id}' from database"  # noqa
        )
        relationship = (
            self.bm.session.query(DepsAssociation)
            .filter(
                DepsAssociation.dependant_id == template_id,
                DepsAssociation.dependee_id == dependency_id,
            )
            .one()
        )
        self.logger.debug(
            f"Deleting depencency from templates with ids '{template_id}' and '{dependency_id}' from database"  # noqa
        )
        self.bm.session.delete(relationship)

    def update_db_template_template_library(
        self, id: int, template_library_id: int
    ) -> None:
        """Update database template.

        :param id: id of DBTemplate
        :type id: str
        :param name: id of the new template_library
        :type name: int
        """
        db_template = self.get_db_template(id)
        self.logger.debug(
            f"Updating template library for template with id '{id}' from library with id '{db_template.template_library_id}' to '{template_library_id}'"  # noqa
        )
        db_template.template_library_id = template_library_id

    def delete_db_template(self, id: int) -> None:
        """Delete database template.

        :param id: id of deleted DBTemplate
        :type id: str
        """
        db_template = self.get_db_template(id)

        self.logger.debug(f"Deleting template '{db_template.name}' from database")
        self.bm.session.delete(db_template)
