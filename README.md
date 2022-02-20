# [![Documentation Status](https://readthedocs.org/projects/buildingmotif/badge/?version=latest)](https://buildingmotif.readthedocs.io/en/latest/?badge=latest) [![codecov](https://codecov.io/gh/haneslinger/BuildingMotif/branch/main/graph/badge.svg?token=2SNN5HPOHL)](https://codecov.io/gh/haneslinger/BuildingMotif)

# BuildingMOTIF

The Building Metadata OnTology Interoperability Framework (BuildingMOTIF)...

# Set up for Development 

Requirements:
- Python >= 3.9.0
- [Poetry](https://python-poetry.org/docs/)

Simply clone and run `poetry install`.
# QuickStart

To test, run 
``` 
poetry run pytest
```
To format and lint, run
```
poetry run black .
poetry run isort .
poetry run pylama
