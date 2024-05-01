"""
Generates tests automatically
"""
import glob
from pathlib import Path

import pytest

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library


def pytest_generate_tests(metafunc):
    """
    Generates BuildingMOTIF tests for a variety of contexts
    """

    # validates that example files pass validation
    if "notebook" in metafunc.fixturenames:
        notebook_files = [
            Path(notebook)
            for notebook in glob.glob("notebooks/**/*.ipynb", recursive=True)
        ]

        metafunc.parametrize("notebook", notebook_files)

    if "shacl_engine" in metafunc.fixturenames:
        shacl_engine = {"pyshacl", "topquadrant"}
        metafunc.parametrize("shacl_engine", shacl_engine)

    ## validate 223P libraries and templates
    # libraries = ["libraries/ashrae/223p/nrel-templates"]

    ## skip these templates because they require additional context to be loaded,
    ## and are covered by other template tests
    # to_skip_223p = {
    #    "nrel-templates": {
    #        "sensor",
    #        "differential-sensor",
    #        "air-outlet-cp",
    #        "air-inlet-cp",
    #        "water-outlet-cp",
    #        "water-inlet-cp",
    #        "duct",
    #        "junction",
    #    }
    # }

    # if "library_path_223p" in metafunc.fixturenames:
    #    metafunc.parametrize("library_path_223p", libraries)

    # if (
    #    "library_path_223p" in metafunc.fixturenames
    #    and "template_223p" in metafunc.fixturenames
    # ):
    #    bm = BuildingMOTIF("sqlite://")

    #    templates = []
    #    # load library
    #    for library_path in libraries:
    #        lib = Library.load(directory=library_path)
    #        bm.session.commit()

    #        for templ in lib.get_templates():
    #            if templ.name in to_skip_223p[lib.name]:
    #                continue
    #            templates.append(templ.name)
    #    bm.close()
    #    BuildingMOTIF.clean()

    #    metafunc.parametrize("template_223p", templates)

    ## validate Brick libraries and temmplates
    # brick_libraries = ["libraries/ashrae/guideline36"]
    # if "library_path_brick" in metafunc.fixturenames:
    #    metafunc.parametrize("library_path_brick", brick_libraries)

    # if (
    #    "library_path_brick" in metafunc.fixturenames
    #    and "template_brick" in metafunc.fixturenames
    # ):
    #    bm = BuildingMOTIF("sqlite://")

    #    Library.load(ontology_graph="libraries/brick/Brick-full.ttl")
    #    templates = []
    #    # load library
    #    for library_path in brick_libraries:
    #        lib = Library.load(directory=library_path)
    #        bm.session.commit()

    #        for templ in lib.get_templates():
    #            templates.append(templ.name)
    #    bm.close()
    #    BuildingMOTIF.clean()

    #    metafunc.parametrize("template_brick", templates)


@pytest.fixture
def bm():
    """
    BuildingMotif instance for tests involving dataclasses and API calls
    """
    bm = BuildingMOTIF("sqlite://")
    # add tables to db
    bm.setup_tables()

    yield bm
    bm.close()
    # clean up the singleton so that tables are re-created correctly later
    BuildingMOTIF.clean()
