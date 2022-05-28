from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

import rdflib

from buildingmotif.dataclasses.template import Template
from buildingmotif.tables import DBTemplate
from buildingmotif.utils import get_building_motif, get_template_parts_from_shape

if TYPE_CHECKING:
    from buildingmotif.building_motif import BuildingMotif


@dataclass
class TemplateLibrary:
    """Collection of Templates. This class mirrors DBTemplateLibrary."""

    _id: int
    _name: str
    _bm: "BuildingMotif"

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

    @classmethod
    def load(cls, id: int) -> "TemplateLibrary":
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
    def from_ontology(cls, ontology: rdflib.Graph) -> "TemplateLibrary":
        """Load a template library from an ontology graph. This proceeds as follows.
        First, get all entities in the graph that are instances of *both* owl:Class
        and sh:NodeShape. (this is "candidates")

        For each candidate, use the utility function to parse the NodeShape and turn
        it into a Template.
        """
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
        for candidate in candidates:
            assert isinstance(candidate, rdflib.URIRef)
            partial_body, deps = get_template_parts_from_shape(candidate, ontology)
            templ = lib.create_template(str(candidate), ["name"], partial_body)
            setattr(templ, "__deps__", deps)
            template_id_lookup[str(candidate)] = templ.id

        # now that we have all the templates, we can populate the dependencies
        for template in lib.get_templates():
            if not hasattr(template, "__deps__"):
                continue
            deps = getattr(template, "__deps__")
            for dep in deps:
                dependee = Template.load(template_id_lookup[dep["rule"]])
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
        self, name: str, head: List[str], body: Optional[rdflib.Graph] = None
    ) -> Template:
        """Create Template in this Template Library

        :param name: name
        :type name: str
        :param head: variables in template body
        :type head: list[str]
        :return: created Template
        :rtype: Template
        """
        db_template = self._bm.table_connection.create_db_template(name, head, self._id)
        body = self._bm.graph_connection.create_graph(
            db_template.body_id, body if body else rdflib.Graph()
        )

        return Template(
            _id=db_template.id,
            _name=db_template.name,
            _head=db_template.head,
            body=body,
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
