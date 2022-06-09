import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import rdflib
import yaml
from rdflib.util import guess_format

from buildingmotif import get_building_motif
from buildingmotif.database.tables import DBTemplate
from buildingmotif.dataclasses import Template
from buildingmotif.template_compilation import compile_template_spec
from buildingmotif.utils import get_template_parts_from_shape

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF


@dataclass
class TemplateLibrary:
    """Collection of Templates. This class mirrors DBTemplateLibrary."""

    _id: int
    _name: str
    _bm: "BuildingMOTIF"

    @classmethod
    def create(cls, name: str) -> "TemplateLibrary":
        """create new Template Library

        :param name: tl name
        :type name: str
        :return: new TemplateLibrary
        :rtype: TemplateLibrary
        """
        bm = get_building_motif()
        db_template_library = bm.table_connection.create_db_template_library(name)

        return cls(_id=db_template_library.id, _name=db_template_library.name, _bm=bm)

    # TODO: load library from URI? Does the URI identify the library uniquely?
    @classmethod
    def load(
        cls,
        db_id: Optional[int] = None,
        ontology_graph: Optional[str] = None,
        directory: Optional[str] = None,
    ) -> "TemplateLibrary":
        if db_id is not None:
            return cls._load_from_db(db_id)
        elif ontology_graph is not None:
            ontology = rdflib.Graph()
            ontology.parse(ontology_graph, format=guess_format(ontology_graph))
            return cls._load_from_ontology_graph(ontology)
        elif directory is not None:
            return cls._load_from_directory(pathlib.Path(directory))
        else:
            raise Exception("No library information provided")

    @classmethod
    def _load_from_db(cls, id: int) -> "TemplateLibrary":
        """load Template Library from db

        :param id: id of template library
        :type id: int
        :return: TemplateLibrary
        :rtype: TemplateLibrary
        """
        bm = get_building_motif()
        db_template_library = bm.table_connection.get_db_template_library(id)

        return cls(_id=db_template_library.id, _name=db_template_library.name, _bm=bm)

    @classmethod
    def _load_from_ontology_graph(cls, ontology: rdflib.Graph) -> "TemplateLibrary":
        """Load a template library from an ontology graph. This proceeds as follows.
        First, get all entities in the graph that are instances of *both* owl:Class
        and sh:NodeShape. (this is "candidates")

        For each candidate, use the utility function to parse the NodeShape and turn
        it into a Template.
        """
        # TODO: handle shapes (eventually)

        # get the name of the ontology; this will be the name of the library
        # any=False will raise an error if there is more than one ontology defined  in the graph
        ontology_name = ontology.value(
            predicate=rdflib.RDF.type, object=rdflib.OWL.Ontology, any=False
        )
        # create the library
        lib = cls.create(ontology_name)
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
            templ = lib.create_template(str(candidate), ["name"], partial_body)
            dependency_cache[templ.id] = deps
            template_id_lookup[str(candidate)] = templ.id

        # now that we have all the templates, we can populate the dependencies
        for template in lib.get_templates():
            if template.id not in dependency_cache:
                continue
            for dep in dependency_cache[template.id]:
                if dep["rule"] in template_id_lookup:
                    dependee = Template.load(template_id_lookup[dep["rule"]])
                    template.add_dependency(dependee, dep["args"])
                else:
                    print(f"Warning: could not find dependee {dep['rule']}")
        return lib

    @classmethod
    def _load_from_directory(cls, directory: pathlib.Path) -> "TemplateLibrary":
        """
        Load a library from a directory. Templates are read from .yml files
        in the directory. The name of the library is given by the name of the directory
        """
        # TODO: handle shapes (eventually)

        lib = cls.create(directory.name)
        template_id_lookup: Dict[str, int] = {}
        dependency_cache: Dict[int, List[Dict[Any, Any]]] = {}
        # read all .yml files
        for file in directory.rglob("*.yml"):
            contents = yaml.load(open(file, "r"), Loader=yaml.FullLoader)
            for templ_name, templ_spec in contents.items():
                # compile the template body using its rules
                templ_spec = compile_template_spec(templ_spec)
                # input name of template
                templ_spec.update({"name": templ_name})
                # remove dependencies so we can resolve them to their IDs later
                deps = templ_spec.pop("dependencies", [])
                templ_spec["optional_args"] = templ_spec.pop("optional", [])
                templ = lib.create_template(**templ_spec)
                dependency_cache[templ.id] = deps
                template_id_lookup[templ.name] = templ.id
        # now that we have all the templates, we can populate the dependencies
        for template in lib.get_templates():
            if template.id not in dependency_cache:
                continue
            for dep in dependency_cache[template.id]:
                if dep["rule"] in template_id_lookup:
                    # local lookup
                    dependee = Template.load(template_id_lookup[dep["rule"]])
                else:
                    # global lookup; returns fist template with given name
                    # TODO: this is not ideal!
                    # TODO: include a field for the template library we are loading from.
                    # Shouldn't need to touch the database
                    dependee = Template.load_by_name(dep["rule"])
                template.add_dependency(dependee, dep["args"])
        return lib

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
        self._bm.table_connection.update_db_template_library_name(self._id, new_name)
        self._name = new_name

    def create_template(
        self,
        name: str,
        head: List[str],
        body: Optional[rdflib.Graph] = None,
        optional_args: Optional[List[str]] = None,
    ) -> Template:
        """Create Template in this Template Library

        :param name: name
        :type name: str
        :param head: variables in template body
        :type head: list[str]
        :param body: template body
        :type body: rdflib.Graph
        :param optional_args: optional parameters for the template
        :type optional_args: list[str]
        :return: created Template
        :rtype: Template
        """
        db_template = self._bm.table_connection.create_db_template(name, head, self._id)
        body = self._bm.graph_connection.create_graph(
            db_template.body_id, body if body else rdflib.Graph()
        )
        if optional_args is None:
            optional_args = []
        self._bm.table_connection.update_db_template_optional_args(
            db_template.id, optional_args
        )

        return Template(
            _id=db_template.id,
            _name=db_template.name,
            _head=db_template.head,
            body=body,
            optional_args=optional_args,
            _bm=self._bm,
        )

    def get_templates(self) -> List[Template]:
        """get Templates in Library

        :return: list of templates
        :rtype: list[Template]
        """
        db_template_library = self._bm.table_connection.get_db_template_library(
            self._id
        )
        templates: List[DBTemplate] = db_template_library.templates
        return [Template.load(t.id) for t in templates]

    def get_template_by_name(self, name: str) -> Template:
        """
        Return template within this library with the given name, if any
        """
        dbt = self._bm.table_connection.get_db_template_by_name(name)
        if dbt.template_library_id != self._id:
            raise ValueError(f"Template {name} not in library {self._name}")
        return Template.load(dbt.id)
