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

    libraries = ["libraries/ashrae/223p/nrel-templates"]
    # validates 223P libraries
    if "library_path_223p" in metafunc.fixturenames:

        metafunc.parametrize("library_path_223p", libraries)

    if (
        "library_path_223p" in metafunc.fixturenames
        and "template_223p" in metafunc.fixturenames
    ):
        bm = BuildingMOTIF("sqlite://")
        bm.setup_tables()

        templates = []
        # load library
        for library_path in libraries:
            lib = Library.load(directory=library_path)
            bm.session.commit()

            for templ in lib.get_templates():
                templates.append(templ.name)

        metafunc.parametrize("template_223p", templates)


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
