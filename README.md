# BuildingMotif [![codecov](https://codecov.io/gh/haneslinger/BuildingMotif/branch/main/graph/badge.svg?token=2SNN5HPOHL)](https://codecov.io/gh/haneslinger/BuildingMotif)

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
