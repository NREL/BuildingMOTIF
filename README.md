# BuildingMotif [![codecov](https://codecov.io/gh/NREL/BuildingMOTIF/branch/main/graph/badge.svg?token=HAFSYH45NX)](https://codecov.io/gh/NREL/BuildingMOTIF)
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
