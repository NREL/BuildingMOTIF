import uuid
from typing import Optional

from sqlalchemy.engine import Engine

from buildingmotif.tables import (
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
        db_model = DBModel(name=name, graph_id=str(uuid.uuid4()))

        self.bm.session.add(db_model)
        self.bm.session.flush()

        return db_model

    def get_all_db_models(self) -> list[DBModel]:
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
        return self.bm.session.query(DBModel).filter(DBModel.id == id).one()

    def update_db_model_name(self, id: int, name: Optional[str]) -> None:
        """Update database model.

        :param id: id of DBModel
        :type id: str
        :param name: new name
        :type name: str
        """
        db_model = self.bm.session.query(DBModel).filter(DBModel.id == id).one()
        db_model.name = name

    def delete_db_model(self, id: int) -> None:
        """Delete database model.

        :param id: id of deleted DBModel
        :type id: str
        """
        db_model = self.bm.session.query(DBModel).filter(DBModel.id == id).one()

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

        self.bm.session.add(template_library)
        self.bm.session.flush()

        return template_library

    def get_all_db_template_libraries(self) -> list[DBTemplateLibrary]:
        """Get all database template library.

        :return: all DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        return self.bm.session.query(DBTemplateLibrary).all()

    def get_db_template_library(self, id: int) -> DBTemplateLibrary:
        """Get database template library from id.

        :param id: id of DBTemplateLibrary
        :type id: str
        :return: DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        return (
            self.bm.session.query(DBTemplateLibrary)
            .filter(DBTemplateLibrary.id == id)
            .one()
        )

    def update_db_template_library_name(self, id: int, name: Optional[str]) -> None:
        """Update database template library.

        :param id: id of DBTemplateLibrary
        :type id: str
        :param name: new name
        :type name: str
        """
        db_template_library = (
            self.bm.session.query(DBTemplateLibrary)
            .filter(DBTemplateLibrary.id == id)
            .one()
        )
        db_template_library.name = name

    def delete_db_template_library(self, id: int) -> None:
        """Delete database template library.

        :param id: id of deleted DBTemplateLibrary
        :type id: str
        """
        db_template_library = (
            self.bm.session.query(DBTemplateLibrary)
            .filter(DBTemplateLibrary.id == id)
            .one()
        )

        self.bm.session.delete(db_template_library)

    # template functions

    def create_db_template(
        self, name: str, head: list[str], template_library_id: int
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
        template_library = self.get_db_template_library(template_library_id)
        template = DBTemplate(
            name=name,
            _head=";".join(head),
            body_id=str(uuid.uuid4()),
            template_library=template_library,
        )

        self.bm.session.add(template)
        self.bm.session.flush()

        return template

    def get_all_db_templates(self) -> list[DBTemplate]:
        """Get all database template.

        :return: all DBTemplate
        :rtype: DBTemplate
        """
        return self.bm.session.query(DBTemplate).all()

    def get_db_template(self, id: int) -> DBTemplate:
        """Get database template from id.

        :param id: id of DBTemplate
        :type id: str
        :return: DBTemplate
        :rtype: DBTemplate
        """
        return self.bm.session.query(DBTemplate).filter(DBTemplate.id == id).one()

    def get_db_tempalte_dependancies(self, id: int) -> tuple[tuple[int, list[str]]]:
        """get a templates dependancies and it args

        if you dont need the args, consider using `template.dependancies`.

        :param id: template id
        :type id: int
        :return: tuple of tuple, where each tuple has 1. the dependant_id, and 2. it's args
        :rtype: tuple[tuple[int, list[str]]]
        """
        relationships = (
            self.bm.session.query(DepsAssociation)
            .filter(DepsAssociation.dependant_id == id)
            .all()
        )

        return tuple([(r.dependee_id, r.args) for r in relationships])

    def update_db_template_name(self, id: int, name: Optional[str]) -> None:
        """Update database template.

        :param id: id of DBTemplate
        :type id: str
        :param name: new name
        :type name: str
        """
        db_template = (
            self.bm.session.query(DBTemplate).filter(DBTemplate.id == id).one()
        )
        db_template.name = name

    def add_template_dependancy(
        self, template_id: int, dependancy_id: int, args: list[str]
    ):
        dependancy = self.get_db_template(dependancy_id)
        if len(args) != len(dependancy.head):
            raise ValueError(
                f"len of args must equal the len of head of the dependancy: \
                    {len(args)} != {len(dependancy.head)}"
            )

        relationship = DepsAssociation(
            dependant_id=template_id, dependee_id=dependancy_id, _args=";".join(args)
        )

        self.bm.session.add(relationship)
        self.bm.session.flush()

    def remove_template_dependancy(self, template_id: int, dependancy_id: int):
        relationship = (
            self.bm.session.query(DepsAssociation)
            .filter(
                DepsAssociation.dependant_id == template_id,
                DepsAssociation.dependee_id == dependancy_id,
            )
            .one()
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
        db_template = (
            self.bm.session.query(DBTemplate).filter(DBTemplate.id == id).one()
        )
        db_template.template_library = template_library_id

    def delete_db_template(self, id: int) -> None:
        """Delete database template.

        :param id: id of deleted DBTemplate
        :type id: str
        """
        db_template = (
            self.bm.session.query(DBTemplate).filter(DBTemplate.id == id).one()
        )

        self.bm.session.delete(db_template)
