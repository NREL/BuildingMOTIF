from typing import Optional

from rdflib import Graph, Literal, Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from buildingmotif.ingresses.bacnet import BACnetNetwork


class IngressHandler:
    def __init__(self, bm: BuildingMOTIF):
        self.bm = bm


class BrickBACnetIngressHandler(IngressHandler):
    BNS = Namespace("urn:brick_bacnet_scan/")

    def __init__(self, bm: BuildingMOTIF, subnet: Optional[str] = None):
        super().__init__(bm)
        self.bacnet_lib = Library.load(directory="libraries/bacnet")
        self.net = BACnetNetwork(subnet)
        self.device_template = self.bacnet_lib.get_template_by_name("brick-device")
        self.object_template = self.bacnet_lib.get_template_by_name("brick-point")

    def add_to_model(self, m: Model, ns: Namespace = BNS):
        """
        Adds metadata from the BACnet network into the given model
        """
        for dev in self.net.devices:
            dev_graph = self.device_template.evaluate(
                {"name": ns[dev.device_id], "instance-number": Literal(dev.device_id)}
            )
            assert isinstance(dev_graph, Graph)
            m.add_graph(dev_graph)

        for ((_dev_addr, dev_id), point) in self.net.objects.items():
            obj_graph = self.object_template.evaluate(
                {
                    "name": ns[f"{point['name']}-{point['id']}"],
                    "identifier": Literal(f"{point['type']},{point['id']}"),
                    "obj-name": Literal(point["name"]),
                    "device": ns[dev_id],
                }
            )
            assert isinstance(obj_graph, Graph)
            m.add_graph(obj_graph)
