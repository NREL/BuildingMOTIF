"""
Generates tests automatically
"""
import glob
from pathlib import Path


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
