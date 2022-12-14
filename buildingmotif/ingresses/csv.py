from csv import DictReader
from functools import cached_property
from pathlib import Path
from typing import List, Optional

from openpyxl import load_workbook
from rdflib import Graph, Namespace

from buildingmotif.ingresses.base import IngressHandler, Record


class CSVIngress(IngressHandler):
    """
    Reads rows from a CSV file and exposes them as records.
    The type of the record is the name of the CSV file
    """

    def __init__(self, filename: Path):
        self.filename = filename

    @cached_property
    def records(self) -> Optional[List[Record]]:
        records = []
        rdr = DictReader(open(self.filename))
        for row in rdr:
            rec = Record(
                rtype=str(self.filename),
                fields=row,
            )
            records.append(rec)

        return records

    def graph(self, _ns: Namespace) -> Optional[Graph]:
        return None


class XLSXIngress(IngressHandler):
    def __init__(self, filename: Path):
        self.filename = filename

    @cached_property
    def records(self) -> Optional[List[Record]]:
        records = []
        wb = load_workbook(self.filename)
        for sheetname in wb.sheetnames:
            sheet = wb[sheetname]
            columns = [sheet.cell(1, c + 1).value for c in range(sheet.max_column)]
            for row in range(2, sheet.max_row + 1):
                fields = {
                    columns[c]: sheet.cell(row, c + 1).value
                    for c in range(sheet.max_column)
                }
                records.append(
                    Record(
                        rtype=sheetname,
                        fields=fields,
                    )
                )
        return records

    def graph(self, _ns: Namespace) -> Optional[Graph]:
        return None
