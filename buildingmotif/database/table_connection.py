import uuid
from itertools import chain
from typing import Dict, List, Optional, Tuple

from sqlalchemy.engine import Engine

from buildingmotif.database.tables import (
    Base,
    DBModel,
    DBTemplate,
    DBTemplateLibrary,
    DepsAssociation,
)
from buildingmotif.namespaces import PARAM


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

    def get_all_db_template_libraries(self) -> List[DBTemplateLibrary]:
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

    def get_db_template_library_by_name(self, name: str) -> DBTemplateLibrary:
        """Get database template library from id.

        :param name: name of DBTemplateLibrary
        :type name: str
        :return: DBTemplateLibrary
        :rtype: DBTemplateLibrary
        """
        return (
            self.bm.session.query(DBTemplateLibrary)
            .filter(DBTemplateLibrary.name == name)
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
            name=name,
            body_id=str(uuid.uuid4()),
            optional_args=[],
            template_library=template_library,
        )

        self.bm.session.add(template)
        self.bm.session.flush()

        return template

    def get_all_db_templates(self) -> List[DBTemplate]:
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

    def get_db_template_by_name(self, name: str) -> DBTemplate:
        """Get database template from id.

        :param name: name of DBTemplate
        :type name: str
        :return: DBTemplate
        :rtype: DBTemplate
        """
        return self.bm.session.query(DBTemplate).filter(DBTemplate.name == name).one()

    def get_db_template_dependencies(self, id: int) -> Tuple[DepsAssociation, ...]:
        """Get a template's dependencies and its arguments.
        If you don't need the arguments, consider using `template.dependencies`.

        :param id: template id
        :type id: int
        :return: tuple of tuple, where each tuple has 1. the dependant_id, and 2. it's args
        :rtype: tuple[tuple[int, list[str]]]
        """
        return tuple(
            self.bm.session.query(DepsAssociation)
            .filter(DepsAssociation.dependant_id == id)
            .all()
        )

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

    def update_db_template_optional_args(
        self, id: int, optional_args: List[str]
    ) -> None:
        """Update database template.

        :param id: id of DBTemplate
        :type id: str
        :param optional_args: new list of optional_args
        :type name: List[str]
        """
        db_template = (
            self.bm.session.query(DBTemplate).filter(DBTemplate.id == id).one()
        )
        db_template.optional_args = optional_args

    def add_template_dependency(
        self, template_id: int, dependency_id: int, args: Dict[str, str]
    ):
        """Create dependency between two templates.

        :param template_id: dependant template id
        :type template_id: int
        :param dependency_id: dependency template id
        :type dependency_id: int
        :param args: mapping of dependency params to dependant params
        :type args: Dict[str, str]
        :raises ValueError: if all dependee required_params not in args
        :raises ValueError: if dependant and dependency template don't share a library
        """
        templ = self.get_db_template(template_id)
        graph = self.bm.graph_connection.get_graph(templ.body_id)
        nodes = chain.from_iterable(graph.triples((None, None, None)))
        params = {str(p)[len(PARAM) :] for p in nodes if str(p).startswith(PARAM)}

        # TODO: do we need this kind of check?
        if "name" not in args.keys():
            raise ValueError(
                f"The name parameter is required for the dependency '{templ.name}'"
            )
        if len(params) > 0 and args["name"] not in params:
            raise ValueError(
                "The name parameter of the dependency must be bound to a param in this template."
                f"'name' was bound to {args['name']} but available params are {params}"
            )

        # In the past we had a check here to make sure the two templates were in the same library.
        # This has been removed because it wasn't actually necessary, but we may add it back in
        # in the future.

        relationship = DepsAssociation(
            dependant_id=template_id,
            dependee_id=dependency_id,
            args=args,
        )

        self.bm.session.add(relationship)
        self.bm.session.flush()

    def remove_template_dependency(self, template_id: int, dependency_id: int):
        """Remove dependency between two templates.

        :param template_id: dependant template id
        :type template_id: int
        :param dependency_id: dependency template id
        :type dependency_id: int
        """
        relationship = (
            self.bm.session.query(DepsAssociation)
            .filter(
                DepsAssociation.dependant_id == template_id,
                DepsAssociation.dependee_id == dependency_id,
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
