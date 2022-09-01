import logging
import uuid
from itertools import chain
from typing import Dict, List, Tuple

from sqlalchemy.engine import Engine

from buildingmotif.database.tables import (
    DBLibrary,
    DBModel,
    DBShapeCollection,
    DBTemplate,
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
        self.logger = logging.getLogger(__name__)
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
        self.logger.debug(f"Creating model: '{name}', with graph: '{graph_id}'")
        db_model = DBModel(name=name, graph_id=graph_id)

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
        db_model = self.bm.session.query(DBModel).filter(DBModel.id == id).one()
        return db_model

    def get_db_model_by_name(self, name: str) -> DBModel:
        """Get database model from name.

        :param name: name of DBModel
        :type name: str
        :return: DBModel
        :rtype: DBModel
        """
        db_model = self.bm.session.query(DBModel).filter(DBModel.name == name).one()
        return db_model

    def update_db_model_name(self, id: int, name: str) -> None:
        """Update database model.

        :param id: id of DBModel
        :type id: str
        :param name: new name
        :type name: str
        """
        db_model = self.get_db_model(id)
        self.logger.debug(f"Updating model name from: '{db_model.name}' to: '{name}'")
        db_model.name = name

    def delete_db_model(self, id: int) -> None:
        """Delete database model.

        :param id: id of deleted DBModel
        :type id: str
        """

        db_model = self.get_db_model(id)
        self.logger.debug(f"Deleting model: '{db_model.name}'")
        self.bm.session.delete(db_model)

    # shape collection functions
    def create_db_shape_collection(self) -> DBShapeCollection:
        """Create a database shape collection.

        :return: DBShapeCollection
        :rtype: DBShapeCollection
        """
        db_shape_collection = DBShapeCollection(graph_id=str(uuid.uuid4()))

        self.bm.session.add(db_shape_collection)
        self.bm.session.flush()

        return db_shape_collection

    def get_all_db_shape_collections(self) -> List[DBShapeCollection]:
        """Get all database shape collections.

        :return: all DBShapeCollections
        :rtype: DBShapeCollection
        """
        return self.bm.session.query(DBShapeCollection).all()

    def get_db_shape_collection(self, id: int) -> DBShapeCollection:
        """Get database shape collection from id.

        :param id: id of DBShapeCollection
        :type id: str
        :return: DBShapeCollection
        :rtype: DBShapeCollection
        """
        return (
            self.bm.session.query(DBShapeCollection)
            .filter(DBShapeCollection.id == id)
            .one()
        )

    def delete_db_shape_collection(self, id: int) -> None:
        """Delete database shape collection.

        :param id: id of deleted DBShapeCollection
        :type id: str
        """
        db_shape_collection = (
            self.bm.session.query(DBShapeCollection)
            .filter(DBShapeCollection.id == id)
            .one()
        )

        self.bm.session.delete(db_shape_collection)

    # library functions

    def create_db_library(self, name: str) -> DBLibrary:
        """Create database library.

        :param name: name of DBLibrary
        :type name: str
        :return: DBLibrary
        :rtype: DBLibrary
        """
        self.logger.debug(f"Creating shape collection in library: '{name}'")
        shape_collection = DBShapeCollection(graph_id=str(uuid.uuid4()))
        self.bm.session.add(shape_collection)

        self.logger.debug(f"Creating database library: '{name}'")
        library = DBLibrary(name=name, shape_collection=shape_collection)
        self.bm.session.add(library)

        self.bm.session.flush()

        return library

    def get_all_db_libraries(self) -> List[DBLibrary]:
        """Get all database libraries.

        :return: all DBLibrary
        :rtype: DBLibrary
        """
        db_libraries = self.bm.session.query(DBLibrary).all()
        return db_libraries

    def get_db_library_by_id(self, id: int) -> DBLibrary:
        """Get database library by id.

        :param id: id of DBLibrary
        :type id: str
        :return: DBLibrary
        :rtype: DBLibrary
        """
        db_library = self.bm.session.query(DBLibrary).filter(DBLibrary.id == id).one()
        return db_library

    def get_db_library_by_name(self, name: str) -> DBLibrary:
        """Get database library by name.

        :param name: name of DBLibrary
        :type name: str
        :return: DBLibrary
        :rtype: DBLibrary
        """
        return self.bm.session.query(DBLibrary).filter(DBLibrary.name == name).one()

    def update_db_library_name(self, id: int, name: str) -> None:
        """Update database library name.

        :param id: id of DBLibrary
        :type id: str
        :param name: new name
        :type name: str
        """
        db_library = self.get_db_library_by_id(id)
        self.logger.debug(
            f"Updating database library name: '{db_library.name}' -> '{name}'"
        )
        db_library.name = name

    def delete_db_library(self, id: int) -> None:
        """Delete database library.

        :param id: id of deleted DBLibrary
        :type id: str
        """

        db_library = self.get_db_library_by_id(id)

        self.logger.debug(f"Deleting database library: '{db_library.name}'")
        self.bm.session.delete(db_library)

    # template functions

    def create_db_template(self, name: str, library_id: int) -> DBTemplate:
        """Create database template.

        :param name: name of DBTemplate
        :type name: str
        :param library_id: id of the template's library
        :return: DBTemplate
        :rtype: DBTemplate
        """
        self.logger.debug(f"Creating database template: '{name}'")
        library = self.get_db_library_by_id(library_id)
        template = DBTemplate(
            name=name,
            body_id=str(uuid.uuid4()),
            optional_args=[],
            library=library,
        )

        self.bm.session.add(template)
        self.bm.session.flush()

        return template

    def get_all_db_templates(self) -> List[DBTemplate]:
        """Get all database template.

        :return: all DBTemplate
        :rtype: DBTemplate
        """
        db_templates = self.bm.session.query(DBTemplate).all()
        return db_templates

    def get_db_template_by_id(self, id: int) -> DBTemplate:
        """Get database template by id.

        :param id: id of DBTemplate
        :type id: str
        :return: DBTemplate
        :rtype: DBTemplate
        """
        db_template = (
            self.bm.session.query(DBTemplate).filter(DBTemplate.id == id).one()
        )
        return db_template

    def get_db_template_by_name(self, name: str) -> DBTemplate:
        """Get database template from id.

        :param name: name of DBTemplate
        :type name: str
        :return: DBTemplate
        :rtype: DBTemplate
        """
        db_template = (
            self.bm.session.query(DBTemplate).filter(DBTemplate.name == name).one()
        )
        return db_template

    def get_library_defining_db_template(self, id: int) -> DBLibrary:
        """
        Returns the library defining the given template
        """
        return self.get_db_template_by_id(id).library

    def get_db_template_dependencies(self, id: int) -> Tuple[DepsAssociation, ...]:
        """Get a template's dependencies and its arguments.
        If you don't need the arguments, consider using `template.dependencies`.

        :param id: template id
        :type id: int
        :return: tuple of tuple, where each tuple has 1. the dependant_id, and 2. it's args
        :rtype: tuple[tuple[int, list[str]]]
        """
        db_template_dependencies = tuple(
            self.bm.session.query(DepsAssociation)
            .filter(DepsAssociation.dependant_id == id)
            .all()
        )
        return db_template_dependencies

    def update_db_template_name(self, id: int, name: str) -> None:
        """Update database template name.

        :param id: id of DBTemplate
        :type id: str
        :param name: new name
        :type name: str
        """
        db_template = self.get_db_template_by_id(id)
        self.logger.debug(
            f"Updating database template name: '{db_template.name}' -> '{name}'"
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
        self.logger.debug(
            f"Creating depencency from templates with ids: '{template_id}' and: '{dependency_id}'"
        )
        templ = self.get_db_template_by_id(template_id)
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

        existing_deps = (
            self.bm.session.query(DepsAssociation)
            .filter(
                DepsAssociation.dependant_id == template_id,
                DepsAssociation.dependee_id == dependency_id,
            )
            .all()
        )
        if any(map(lambda x: x.args == args, existing_deps)):
            raise ValueError(
                f"{templ.name} already depends on {dependency_id} with args {args}"
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
        self.logger.debug(
            f"Deleting depencency from templates with ids: '{template_id}' and: '{dependency_id}'"  # noqa
        )

        relationship = (
            self.bm.session.query(DepsAssociation)
            .filter(
                DepsAssociation.dependant_id == template_id,
                DepsAssociation.dependee_id == dependency_id,
            )
            .one()
        )
        self.bm.session.delete(relationship)

    def update_db_template_library(self, id: int, library_id: int) -> None:
        """Update database template library.

        :param id: id of DBTemplate
        :type id: str
        :param name: id of the new library
        :type name: int
        """
        db_template = self.get_db_template_by_id(id)
        self.logger.debug(
            f"Updating database template library: '{db_template.library_id}' -> '{library_id}'"  # noqa
        )
        db_template.library_id = library_id

    def delete_db_template(self, id: int) -> None:
        """Delete database template.

        :param id: id of deleted DBTemplate
        :type id: str
        """
        db_template = self.get_db_template_by_id(id)
        self.logger.debug(f"Deleting template: '{db_template.name}'")

        self.bm.session.delete(db_template)
