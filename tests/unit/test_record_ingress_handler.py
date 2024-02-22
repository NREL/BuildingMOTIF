from pathlib import Path

from buildingmotif.ingresses.base import Record, RecordIngressHandler


def test_ingress_dump_load(bm, tmp_path: Path):
    records = [
        Record("a", {"a": 1, "b": 2}),
        Record("b", {"b": 1, "a": 2}),
    ]

    output_file = tmp_path / "output.json"

    ingress_handler_1 = RecordIngressHandler.__new__(RecordIngressHandler)
    ingress_handler_1.records = records
    ingress_handler_1.dump(output_file)

    ingress_handler_2 = RecordIngressHandler.load(output_file)
    ingress_records = ingress_handler_2.records

    assert ingress_records == records
