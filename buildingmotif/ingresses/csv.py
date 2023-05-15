from csv import DictReader
from functools import cached_property
from pathlib import Path
from typing import List

from buildingmotif.ingresses.base import Record, RecordIngressHandler


class CSVIngress(RecordIngressHandler):
    """Reads rows from a CSV file and exposes them as records.
    The type of the record is the name of the CSV file
    """

    def __init__(self, filename: Path = None, data: str = None):
        if filename is not None and data is not None:
            raise ValueError("Both filename and data are defined.")

        if filename:
            self.dict_reader = DictReader(open(filename))
            self.rtype = filename

        elif data:
            self.dict_reader = DictReader(data, delimiter=",")
            self.rtype = "data stream"

        else:
            raise ValueError("Either filename or data must be defined.")

    @cached_property
    def records(self) -> List[Record]:
        records = []
        for row in self.dict_reader:
            rec = Record(
                rtype=self.rtype,
                fields=row,
            )
            records.append(rec)

        return records
