import logging
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Union

import pyshacl
import rdflib
import sqlalchemy
import yaml
from pkg_resources import resource_exists, resource_filename
from rdflib.exceptions import ParserError
from rdflib.plugins.parsers.notation3 import BadSyntax
from rdflib.util import guess_format

from buildingmotif import get_building_motif
from buildingmotif.database.tables import DBLibrary, DBTemplate
from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.dataclasses.template import Template
from buildingmotif.namespaces import XSD
from buildingmotif.template_compilation import compile_template_spec
from buildingmotif.utils import get_ontology_files, get_template_parts_from_shape

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF


@dataclass
class _template_dependency:
    """Represents early-bound (template_id) or late-bound (template_name and
    library) dependency of a template on another template.
    """

    template_name: str
    bindings: Dict[str, Any]
    library: str
    template_id: Optional[int] = None

    def __repr__(self):
        return (
            f"dep<name={self.template_name} bindings={self.bindings} "
            f"library={self.library} id={self.template_id}>"
        )

    @classmethod
    def from_dict(
        cls, d: Dict[str, Any], dependent_library_name: str
    ) -> "_template_dependency":
        """Creates a py:class:`_template_dependency` from a dictionary.

        :param d: dictionary
        :type d: Dict[str, Any]
        :param dependent_library_name: library name
        :type dependent_library_name: str
        :return: the _template_dependency from the dict
        :rtype: _template_dependency
        """
        template_name = d["template"]
        bindings = d.get("args", {})
        library = d.get("library", dependent_library_name)
        template_id = d.get("template_id")
        return cls(template_name, bindings, library, template_id)

    def to_template(self, id_lookup: Dict[str, int]) -> Template:
        """Resolve this dependency to a template.

        :param id_lookup: a local cache of {name: id} for uncommitted templates
        :type id_lookup: Dict[str, int]
        :return: the template instance this dependency points to
        :rtype: Template
        """
        # direct lookup if id is provided
        if self.template_id is not None:
            return Template.load(self.template_id)
        # if id is not provided, look at our local 'cache' of to-be-committed
        # templates for the id (id_lookup)
        if self.template_name in id_lookup:
            return Template.load(id_lookup[self.template_name])
        # if not in the local cache, then search the database for the template
        # within the given library
        library = Library.load(name=self.library)
        return library.get_template_by_name(self.template_name)


@dataclass
class Library:
    """This class mirrors :py:class:`database.tables.DBLibrary`."""

    _id: int
    _name: str
    _bm: "BuildingMOTIF"

    @classmethod
    def create(cls, name: str, overwrite: Optional[bool] = True) -> "Library":
        """Create new Library.

        :param name: library name
        :type name: str
        :param overwrite: if True, overwrite the existing copy of the library.
        :type overwrite: Optional[bool]
        :return: new library
        :rtype: Library
        """
        bm = get_building_motif()
        try:
            db_library = bm.table_connection.get_db_library_by_name(name)
            if overwrite:
                cls._clear_library(db_library)
            else:
                logging.warn(
                    f'Library {name} already exists in database. To ovewrite load library with "overwrite=True"'  # noqa
                )
        except sqlalchemy.exc.NoResultFound:
            db_library = bm.table_connection.create_db_library(name)

        return cls(_id=db_library.id, _name=db_library.name, _bm=bm)

    @classmethod
    def _clear_library(cls, library: DBLibrary) -> None:
        """Clear contents of a library.

        :param library: library to clear
        :type library: DBLibrary
        """
        bm = get_building_motif()
        for template in library.templates:  # type: ignore
            bm.session.delete(template)

    # TODO: load library from URI? Does the URI identify the library uniquely?
    # TODO: can we deduplicate shape graphs? use hash of graph?
    @classmethod
    def load(
        cls,
        db_id: Optional[int] = None,
        ontology_graph: Optional[Union[str, rdflib.Graph]] = None,
        directory: Optional[str] = None,
        name: Optional[str] = None,
        overwrite: Optional[bool] = True,
    ) -> "Library":
        """Loads a library from the database or an external source.
        When specifying a path to load a library or ontology_graph from,
        paths within the buildingmotif.libraries module will be prioritized
        if they resolve.

        :param db_id: the unique id of the library in the database,
            defaults to None
        :type db_id: Optional[int], optional
        :param ontology_graph: a path to a serialized RDF graph,
            defaults to None
        :type ontology_graph: Optional[str|rdflib.Graph], optional
        :param directory: a path to a directory containing a library,
            or an rdflib graph, defaults to None
        :type directory: Optional[str], optional
        :param name: the name of the library inside the database,
            defaults to None
        :type name: Optional[str], optional
        :param overwrite: if true, replace any existing copy of the
            library, defaults to True
        :type overwrite: Optional[true], optional
        :return: the loaded library
        :rtype: Library
        :raises Exception: if the library cannot be loaded
        """
        if db_id is not None:
            return cls._load_from_db(db_id)
        elif ontology_graph is not None:
            if isinstance(ontology_graph, str):
                ontology_graph_path = ontology_graph
                if resource_exists("buildingmotif.libraries", ontology_graph_path):
                    logging.debug(f"Loading builtin library: {ontology_graph_path}")
                    ontology_graph_path = resource_filename(
                        "buildingmotif.libraries", ontology_graph_path
                    )
                ontology_graph = rdflib.Graph()
                ontology_graph.parse(
                    ontology_graph_path, format=guess_format(ontology_graph_path)
                )
            return cls._load_from_ontology(ontology_graph, overwrite=overwrite)
        elif directory is not None:
            if resource_exists("buildingmotif.libraries", directory):
                logging.debug(f"Loading builtin library: {directory}")
                src = pathlib.Path(
                    resource_filename("buildingmotif.libraries", directory)
                )
            else:
                src = pathlib.Path(directory)
            if not src.exists():
                raise Exception(f"Directory {src} does not exist")
            return cls._load_from_directory(src, overwrite=overwrite)
        elif name is not None:
            bm = get_building_motif()
            db_library = bm.table_connection.get_db_library_by_name(name)
            return cls(_id=db_library.id, _name=db_library.name, _bm=bm)
        else:
            raise Exception("No library information provided")

    @classmethod
    def _load_from_db(cls, id: int) -> "Library":
        """Load library from database by id.

        :param id: id of library
        :type id: int
        :return: library
        :rtype: Library
        """
        bm = get_building_motif()
        db_library = bm.table_connection.get_db_library_by_id(id)

        return cls(_id=db_library.id, _name=db_library.name, _bm=bm)

    @classmethod
    def _load_from_ontology(
        cls, ontology: rdflib.Graph, overwrite: Optional[bool] = True
    ) -> "Library":
        """
        Load a library from an ontology graph. This proceeds as follows.
        First, get all entities in the graph that are instances of *both* owl:Class
        and sh:NodeShape. (this is "candidates")

        For each candidate, use the utility function to parse the NodeShape and turn
        it into a Template.

        :param ontology: the graph to load into BuildingMOTIF and interpret as a Library
        :type ontology: rdflib.Graph
        :param overwrite: if true, overwrite the existing copy of the Library
        :type overwrite: bool
        :return: the loaded Library
        :rtype: "Library"
        """
        # get the name of the ontology; this will be the name of the library
        # any=False will raise an error if there is more than one ontology defined  in the graph
        ontology_name = ontology.value(
            predicate=rdflib.RDF.type, object=rdflib.OWL.Ontology, any=False
        )

        if not overwrite:
            if cls._library_exists(ontology_name):
                logging.warning(
                    f'Library "{ontology_name}" already exists in database and "overwrite=False". Returning existing library.'  # noqa
                )
                return Library.load(name=ontology_name)

        # expand the ontology graph before we insert it into the database. This will ensure
        # that the output of compiled models will not contain triples that really belong to
        # the ontology
        pyshacl.validate(
            data_graph=ontology,
            shacl_graph=ontology,
            ont_graph=ontology,
            advanced=True,
            inplace=True,
            js=True,
        )

        lib = cls.create(ontology_name, overwrite=overwrite)

        class_candidates = set(ontology.subjects(rdflib.RDF.type, rdflib.OWL.Class))
        shape_candidates = set(ontology.subjects(rdflib.RDF.type, rdflib.SH.NodeShape))
        candidates = class_candidates.intersection(shape_candidates)

        # stores the lookup from template *names* to template *ids*
        # this is necessary because while we know the *name* of the dependee templates
        # for each dependent template, we don't know the *id* of the dependee templates,
        # which is necessary to populate the dependencies
        template_id_lookup: Dict[str, int] = {}
        dependency_cache: Dict[int, List[Dict[Any, Any]]] = {}
        for candidate in candidates:
            assert isinstance(candidate, rdflib.URIRef)
            partial_body, deps = get_template_parts_from_shape(candidate, ontology)
            templ = lib.create_template(str(candidate), partial_body)
            dependency_cache[templ.id] = deps
            template_id_lookup[str(candidate)] = templ.id

        lib._resolve_template_dependencies(template_id_lookup, dependency_cache)

        # load the ontology graph as a shape_collection
        shape_col_id = lib.get_shape_collection().id
        assert shape_col_id is not None  # should always pass
        shape_col = ShapeCollection.load(shape_col_id)
        shape_col.add_graph(ontology)

        return lib

    def _load_shapes_from_directory(self, directory: pathlib.Path):
        """Helper method to read all graphs in the given directory into this
        library.

        :param directory: directory containing graph files
        :type directory: pathlib.Path
        """
        shape_col_id = self.get_shape_collection().id
        assert shape_col_id is not None  # this should always pass
        shape_col = ShapeCollection.load(shape_col_id)
        for filename in get_ontology_files(directory):
            try:
                shape_col.graph.parse(filename, format=guess_format(filename))
            except (ParserError, BadSyntax) as e:
                logging.getLogger(__name__).error(
                    f"Could not parse file {filename}: {e}"
                )
                raise e

    @classmethod
    def _load_from_directory(
        cls, directory: pathlib.Path, overwrite: Optional[bool] = True
    ) -> "Library":
        """
        Load a library from a directory.

        Templates are read from YML files in the directory. The name of the
        library is given by the name of the directory.

        :param directory: directory containing a library
        :type directory: pathlib.Path
        :param overwrite: if true, overwrite the existing copy of the Library
        :type overwrite: bool
        :raises e: if cannot create template
        :raises e: if cannot resolve dependencies
        :return: library
        :rtype: Library
        """

        if not overwrite:
            if cls._library_exists(directory.name):
                logging.warn(
                    f'Library "{directory.name}" already exists in database and "overwrite=False". Returning existing library.'  # noqa
                )
                return Library.load(name=directory.name)

        lib = cls.create(directory.name, overwrite=overwrite)

        # setup caches for reading templates
        template_id_lookup: Dict[str, int] = {}
        dependency_cache: Dict[int, List[_template_dependency]] = {}

        # read all .yml files
        for file in directory.rglob("*.yml"):
            lib._read_yml_file(file, template_id_lookup, dependency_cache)
        # now that we have all the templates, we can populate the dependencies
        lib._resolve_template_dependencies(template_id_lookup, dependency_cache)
        # load shape collections from all ontology files in the directory
        lib._load_shapes_from_directory(directory)

        return lib

    @staticmethod
    def _library_exists(library_name: str) -> bool:
        """Checks whether a library with the given name exists in the database."""
        bm = get_building_motif()
        try:
            bm.table_connection.get_db_library_by_name(library_name)
            return True
        except sqlalchemy.exc.NoResultFound:
            return False

    def _resolve_template_dependencies(
        self,
        template_id_lookup: Dict[str, int],
        dependency_cache: Mapping[int, Union[List[_template_dependency], List[dict]]],
    ):
        for template in self.get_templates():
            if template.id not in dependency_cache:
                continue
            for dep in dependency_cache[template.id]:
                if isinstance(dep, dict):
                    if dep["template"] in template_id_lookup:
                        dependee = Template.load(template_id_lookup[dep["template"]])
                        template.add_dependency(dependee, dep["args"])
                    # Now that we have all the templates, we can populate the dependencies.
                    # IGNORES missing XSD imports --- there is really no reason to import the XSD
                    # ontology because the handling is baked into the software processing the RDF
                    # graph. Thus, XSD URIs will always yield import warnings. This is noisy, so we
                    # suppress them.
                    elif not dep["template"].startswith(XSD):
                        logging.warn(
                            f"Warning: could not find dependee {dep['template']}"
                        )
                elif isinstance(dep, _template_dependency):
                    try:
                        dependee = dep.to_template(template_id_lookup)
                        template.add_dependency(dependee, dep.bindings)
                    except Exception as e:
                        logging.warn(f"Warning: could not resolve dependency {dep}")
                        raise e

    def _read_yml_file(
        self,
        file: pathlib.Path,
        template_id_lookup: Dict[str, int],
        dependency_cache: Dict[int, List[_template_dependency]],
    ):
        """Read a YML file into this library. Utility function for `_load_from_directory`."""
        contents = yaml.load(open(file, "r"), Loader=yaml.FullLoader)
        for templ_name, templ_spec in contents.items():
            # compile the template body using its rules
            templ_spec = compile_template_spec(templ_spec)
            # input name of template
            templ_spec.update({"name": templ_name})
            # remove dependencies so we can resolve them to their IDs later
            deps = [
                _template_dependency.from_dict(d, self.name)
                for d in templ_spec.pop("dependencies", [])
            ]
            templ_spec["optional_args"] = templ_spec.pop("optional", [])
            try:
                templ = self.create_template(**templ_spec)
            except Exception as e:
                logging.error(
                    f"Error creating template {templ_name} from file {file}: {e}"
                )
                raise e
            dependency_cache[templ.id] = deps
            template_id_lookup[templ.name] = templ.id

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, new_id):
        raise AttributeError("Cannot modify db id")

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str):
        self._bm.table_connection.update_db_library_name(self._id, new_name)
        self._name = new_name

    def create_template(
        self,
        name: str,
        body: Optional[rdflib.Graph] = None,
        optional_args: Optional[List[str]] = None,
    ) -> Template:
        """Create template in this library.

        :param name: name
        :type name: str
        :param body: template body
        :type body: rdflib.Graph
        :param optional_args: optional parameters for the template
        :type optional_args: list[str]
        :return: created template
        :rtype: Template
        """
        db_template = self._bm.table_connection.create_db_template(name, self._id)
        body = self._bm.graph_connection.create_graph(
            db_template.body_id, body if body else rdflib.Graph()
        )
        # ensure the "param" namespace is bound to the graph
        body.namespace_manager = self._bm.template_ns_mgr
        if optional_args is None:
            optional_args = []
        self._bm.table_connection.update_db_template_optional_args(
            db_template.id, optional_args
        )

        return Template(
            _id=db_template.id,
            _name=db_template.name,
            body=body,
            optional_args=optional_args,
            _bm=self._bm,
        )

    def get_templates(self) -> List[Template]:
        """Get templates from library.

        :return: list of templates
        :rtype: List[Template]
        """
        db_library = self._bm.table_connection.get_db_library_by_id(self._id)
        templates: List[DBTemplate] = db_library.templates
        return [Template.load(t.id) for t in templates]

    def get_shape_collection(self) -> ShapeCollection:
        """Get ShapeCollection from library.

        :return: library's shape collection
        :rtype: ShapeCollection
        """
        db_library = self._bm.table_connection.get_db_library_by_id(self._id)

        return ShapeCollection.load(db_library.shape_collection.id)

    def get_template_by_name(self, name: str) -> Template:
        """Get template by name from library.

        :param name: template name
        :type name: str
        :raises ValueError: if template not in library
        :return: template
        :rtype: Template
        """
        dbt = self._bm.table_connection.get_db_template_by_name(name)
        if dbt.library_id != self._id:
            raise ValueError(f"Template {name} not in library {self._name}")
        return Template.load(dbt.id)
