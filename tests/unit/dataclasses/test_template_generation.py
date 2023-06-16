import csv
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import openpyxl
from rdflib import Namespace
from rdflib.compare import isomorphic

from buildingmotif.building_motif.building_motif import BuildingMOTIF
from buildingmotif.dataclasses import Library
from buildingmotif.ingresses.csv import CSVIngress
from buildingmotif.ingresses.template import TemplateIngress
from buildingmotif.ingresses.xlsx import XLSXIngress

BLDG = Namespace("urn:bldg/")


# utility function for spreadsheet tests
def _add_spreadsheet_row(sheet, bindings):
    num_columns = sheet.max_column
    for column in range(1, num_columns + 1):
        param = sheet.cell(row=1, column=column).value
        sheet.cell(row=2, column=column).value = bindings[param][len(BLDG) :]


def _add_csv_row(params, tempfile, bindings):
    params = [param.strip() for param in params]
    if isinstance(tempfile, StringIO):
        w = csv.writer(tempfile)
        w.writerow([bindings[param][len(BLDG) :] for param in params])
        tempfile.flush()
    else:
        with open(Path(tempfile.name), "a") as f:
            w = csv.writer(f)
            w.writerow([bindings[param][len(BLDG) :] for param in params])


def pytest_generate_tests(metafunc):
    BuildingMOTIF("sqlite://")  # in-memory
    fixture_lib = Library.load(directory="tests/unit/fixtures/templates")
    if metafunc.fixturenames == ["template", "bindings", "filled"]:
        # test simple template, no deps, no optional, no inline
        fan = fixture_lib.get_template_by_name("supply-fan")
        fan_bind, fan_fill = fan.fill(BLDG)

        # test simple template, no deps, WITH optional, no inline
        oad = fixture_lib.get_template_by_name("outside-air-damper")
        oad_bind, oad_fill = oad.fill(BLDG, include_optional=True)

        # test simple template, WITH deps, WITH optional, no inline
        szva = fixture_lib.get_template_by_name("single-zone-vav-ahu")
        szva_bind, szva_fill = szva.fill(BLDG, include_optional=True)

        # test simple template, WITH deps, WITH optional, WITH inline
        szva_inline = fixture_lib.get_template_by_name(
            "single-zone-vav-ahu"
        ).inline_dependencies()
        szva_inline_bind, szva_inline_fill = szva_inline.fill(
            BLDG, include_optional=True
        )

        test_cases = {
            "NOdep-NOoptional-NOinline": (fan, fan_bind, fan_fill),
            "NOdep-WITHoptional-NOinline": (oad, oad_bind, oad_fill),
            "WITHdep-WITHoptional-NOinline": (szva, szva_bind, szva_fill),
            "WITHdep-WITHoptional-WITHinline": (
                szva_inline,
                szva_inline_bind,
                szva_inline_fill,
            ),
        }
        metafunc.parametrize(
            "template,bindings,filled", test_cases.values(), ids=test_cases.keys()
        )


def test_template_generation_inmemory(template, bindings, filled):
    with NamedTemporaryFile(suffix=".xlsx") as dest:
        output = template.generate_spreadsheet()
        assert output is not None
        dest.write(output.getbuffer())

        w = openpyxl.load_workbook(dest.name)
        _add_spreadsheet_row(w.active, bindings)
        w.save(Path(dest.name))

        reader = XLSXIngress(Path(dest.name))
        ing = TemplateIngress(template, None, reader)
        g = ing.graph(BLDG)

        assert isomorphic(
            g, filled
        ), f"Template -> spreadsheet -> ingress -> graph path did not generate a result isomorphic to just filling the template {template.name}"


def test_template_generation_file(template, bindings, filled):
    with NamedTemporaryFile(suffix=".xlsx") as dest:
        output = template.generate_spreadsheet(Path(dest.name))
        assert output is None

        w = openpyxl.load_workbook(dest.name)
        _add_spreadsheet_row(w.active, bindings)
        w.save(Path(dest.name))

        reader = XLSXIngress(Path(dest.name))
        ing = TemplateIngress(template, None, reader)
        g = ing.graph(BLDG)

        assert isomorphic(
            g, filled
        ), f"Template -> spreadsheet -> ingress -> graph path did not generate a result isomorphic to just filling the template {template.name}"


def test_csv_generation_inmemory(template, bindings, filled):
    with NamedTemporaryFile(mode="w", suffix=".csv") as dest:
        output = template.generate_csv()
        assert output is not None
        dest.writelines([output.getvalue()])
        dest.flush()

        params = output.getvalue().split(",")
        _add_csv_row(params, dest, bindings)

        reader = CSVIngress(Path(dest.name))
        ing = TemplateIngress(template, None, reader)
        g = ing.graph(BLDG)

        assert isomorphic(
            g, filled
        ), f"Template -> csv -> ingress -> graph path did not generate a result isomorphic to just filling the template {template.name}"


def test_csv_generation_file(template, bindings, filled):
    with NamedTemporaryFile(mode="w", suffix=".csv") as dest:
        output = template.generate_csv(Path(dest.name))
        assert output is None

        with open(Path(dest.name)) as f:
            params = f.read().strip().split(",")
        _add_csv_row(params, dest, bindings)

        reader = CSVIngress(Path(dest.name))
        ing = TemplateIngress(template, None, reader)
        g = ing.graph(BLDG)

        assert isomorphic(
            g, filled
        ), f"Template -> csv -> ingress -> graph path did not generate a result isomorphic to just filling the template {template.name}"
