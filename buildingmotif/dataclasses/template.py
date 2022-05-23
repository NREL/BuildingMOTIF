from dataclasses import dataclass

import rdflib

from buildingmotif.building_motif.building_motif import (
    BuildingMotif,
    get_building_motif,
)


@dataclass
class Template:
    """Template. This class mirrors DBTemplate."""

    _id: int
    _name: str
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

        return cls(_id=db_template.id, _name=db_template.name, body=body, _bm=bm)

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
