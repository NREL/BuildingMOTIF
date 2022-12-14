from csv import DictReader
from functools import cached_property
from pathlib import Path
from typing import List

from buildingmotif.ingresses.base import Record, RecordIngressHandler


class CSVIngress(RecordIngressHandler):
    """Reads rows from a CSV file and exposes them as records.
    The type of the record is the name of the CSV file
    """

    def __init__(self, filename: Path):
        self.filename = filename

    @cached_property
    def records(self) -> List[Record]:
        records = []
        rdr = DictReader(open(self.filename))
        for row in rdr:
            rec = Record(
                rtype=str(self.filename),
                fields=row,
            )
            records.append(rec)

        return records
