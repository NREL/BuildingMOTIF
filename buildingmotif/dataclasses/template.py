from dataclasses import dataclass

import rdflib

from buildingmotif.building_motif import BuildingMotif
from buildingmotif.utils import get_building_motif


@dataclass
class Template:
    """Template. This class mirrors DBTemplate."""

    _id: int
    _name: str
    _head: tuple[str, ...]
    body: rdflib.Graph
    _bm: BuildingMotif

    @classmethod
    def load(cls, id: int) -> "Template":
        """load Template from db

        :param id: id of template
        :type id: int
        :return: loaded Template
        :rtype: Template
        """
        bm = get_building_motif()
        db_template = bm.table_connection.get_db_template(id)
        body = bm.graph_connection.get_graph(db_template.body_id)

        return cls(
            _id=db_template.id,
            _name=db_template.name,
            _head=db_template.head,
            body=body,
            _bm=bm,
        )

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, new_id):
        raise AttributeError("Cannot modify db id")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name: str) -> None:
        self._bm.table_connection.update_db_template_name(self._id, new_name)
        self._name = new_name

    @property
    def head(self):
        return self._head

    @head.setter
    def head(self, new_head: str) -> None:
        raise AttributeError("Cannot modify head")

    def get_dependancies(self):
        return self._bm.table_connection.get_db_tempalte_dependancies(self.id)

    def add_dependancy(self, dependancy: "Template", args: list[str]) -> None:
        self._bm.table_connection.add_template_dependancy(self.id, dependancy.id, args)

    def remove_dependancy(self, dependancy: "Template") -> None:
        self._bm.table_connection.remove_template_dependancy(self.id, dependancy.id)
