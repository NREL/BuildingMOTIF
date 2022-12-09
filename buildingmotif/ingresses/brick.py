from typing import List, Optional

from rdflib import Graph, Literal, Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library
from buildingmotif.ingresses.bacnet import BACnetNetwork
from buildingmotif.ingresses.base import IngressHandler, Record


def clean_uri(n) -> str:
    if isinstance(n, str):
        return n.replace(" ", "_")
    return str(n)


class BACnetToBrickIngress(IngressHandler):
    BNS = Namespace("urn:brick_bacnet_scan/")

    def __init__(self, bm: BuildingMOTIF, upstream: BACnetNetwork):
        super().__init__(bm)
        self.upstream = upstream
        self.bacnet_lib = Library.load(directory="libraries/bacnet")
        self.device_template = self.bacnet_lib.get_template_by_name("brick-device")
        self.object_template = self.bacnet_lib.get_template_by_name("brick-point")

    def records(self) -> Optional[List[Record]]:
        return None

    def graph(self, ns: Namespace) -> Optional[Graph]:
        g = Graph()
        records = self.upstream.records()
        assert records is not None
        for record in records:
            if record.rtype == "Device":
                dev = record.fields
                device_id = dev["device_id"]
                name = clean_uri(device_id) or clean_uri(dev["address"])
                dev_graph = self.device_template.evaluate(
                    {
                        "name": ns[name],
                        "instance-number": Literal(device_id),
                        "address": Literal(dev["address"]),
                    }
                )
                assert isinstance(dev_graph, Graph)
                g += dev_graph
            elif record.rtype == "Object":
                point = record.fields
                device_id = point["device_id"]
                obj_graph = self.object_template.evaluate(
                    {
                        "name": ns[f"{clean_uri(point['name'])}-{point['address']}"],
                        "identifier": Literal(f"{point['type']},{point['address']}"),
                        "obj-name": Literal(point["name"]),
                        "device": ns[clean_uri(device_id)],
                    }
                )
                assert isinstance(obj_graph, Graph)
                g += obj_graph

        return g
