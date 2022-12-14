from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple

import BAC0
from BAC0.core.devices.Device import Device as BACnetDevice
from rdflib import Graph, Namespace

from buildingmotif.ingresses.base import IngressHandler, Record

# configure logging output
BAC0.log_level("error")


class BACnetNetwork(IngressHandler):
    def __init__(self, ip: Optional[str] = None):
        """
        Reads a BACnet network to discover the devices and objects therein

        :param ip: IP/mask for the host which is canning the networks, defaults to None
        :type ip: Optional[str], optional
        """
        # create the network object; this will handle scans
        # Be a good net citizen: do not ping BACnet devices
        self.network = BAC0.connect(ip=ip, ping=False)
        # initiate discovery of BACnet networks
        self.network.discover()

        self.devices: List[BACnetDevice] = []
        self.objects: Dict[Tuple[str, int], List[dict]] = {}

        # for each discovered Device, create a BAC0.device object
        # This will read the BACnet objects off of the Device.
        # Save the BACnet objects in the objects dictionary
        assert self.network.discoveredDevices is not None
        for (address, device_id) in self.network.discoveredDevices:  # type: ignore
            # set poll to 0 to avoid reading the points regularly
            dev = BAC0.device(address, device_id, self.network, poll=0)
            self.devices.append(dev)
            self.objects[(address, device_id)] = []

            for bobj in dev.points:
                obj = bobj.properties.asdict
                self._clean_object(obj)
                self.objects[(address, device_id)].append(obj)

    def _clean_object(self, obj: Dict[str, Any]):
        if "name" in obj:
            # remove trailing/leading whitespace from names
            obj["name"] = obj["name"].strip()

    @cached_property
    def records(self) -> Optional[List[Record]]:
        """
        Returns a list of the BACnet devices and objects discovered
        in the BACnet network
        """
        records = []
        # make devices
        for (address, device_id) in self.objects.keys():
            records.append(
                Record(
                    rtype="Device",
                    fields={"address": address, "device_id": device_id},
                )
            )
        for (address, device_id), objs in self.objects.items():
            for obj in objs:
                fields = obj.copy()
                fields["device_id"] = device_id
                records.append(
                    Record(
                        rtype="Object",
                        fields=fields,
                    )
                )
        return records

    def graph(self, _ns: Namespace) -> Optional[Graph]:
        """
        Consume the output of .records() to create a graph
        """
        return None
