from typing import Optional

from rdflib import Graph, Literal, Namespace

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from buildingmotif.ingresses.bacnet import BACnetNetwork


def clean_uri(n) -> str:
    if isinstance(n, str):
        return n.replace(" ", "_")
    return str(n)


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
            device_id = dev.properties.device_id
            print(dev.properties)
            name = clean_uri(device_id) or clean_uri(dev.properties.address)
            dev_graph = self.device_template.evaluate(
                {
                    "name": ns[name],
                    "instance-number": Literal(device_id),
                    "address": Literal(dev.properties.address),
                }
            )
            assert isinstance(dev_graph, Graph)
            m.add_graph(dev_graph)

        for ((_dev_addr, dev_id), points) in self.net.objects.items():
            for point in points:
                obj_graph = self.object_template.evaluate(
                    {
                        "name": ns[f"{clean_uri(point['name'])}-{point['address']}"],
                        "identifier": Literal(f"{point['type']},{point['address']}"),
                        "obj-name": Literal(point["name"]),
                        "device": ns[clean_uri(dev_id)],
                    }
                )
                assert isinstance(obj_graph, Graph)
                m.add_graph(obj_graph)
