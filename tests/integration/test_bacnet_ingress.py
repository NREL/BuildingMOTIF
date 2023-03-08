import shlex
import subprocess
from pathlib import Path

import pytest
from rdflib import Namespace

from buildingmotif.dataclasses import Model
from buildingmotif.ingresses import BACnetNetwork, BACnetToBrickIngress
from buildingmotif.namespaces import BACNET, BRICK, RDF

# path to docker compose file
docker_compose_path = Path(__file__).parent / Path("fixtures") / Path("bacnet-network")
# command to start docker compose
docker_compose_start = shlex.split("docker compose up -d")
# command to stop docker compose
docker_compose_stop = shlex.split("docker compose down")


@pytest.mark.integration
def test_bacnet_ingress(bm):
    try:
        subprocess.run(docker_compose_start, cwd=docker_compose_path)
        BLDG = Namespace("urn:building/")
        m = Model.create(BLDG, "test building for bacnet scan")
        bacnet = BACnetNetwork("172.24.0.1/32")
        tobrick = BACnetToBrickIngress(bm, bacnet)
        m.add_graph(tobrick.graph(BLDG))

        devices = list(m.graph.subjects(RDF["type"], BACNET["BACnetDevice"]))
        assert (
            len(devices) == 1
        ), f"Did not find exactly 1 device (found {len(devices)})"
        assert devices[0] == BLDG["599"]  # type: ignore

        objects = list(m.graph.subjects(RDF["type"], BRICK["Point"]))
        assert len(objects) == 2, "Did not find exactly 2 points"
    finally:
        subprocess.run(docker_compose_stop, cwd=docker_compose_path)
