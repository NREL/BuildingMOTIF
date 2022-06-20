# BuildingMOTIF 
[![Documentation Status](https://readthedocs.org/projects/buildingmotif/badge/?version=latest)](https://buildingmotif.readthedocs.io/en/latest/?badge=latest) 
[![codecov](https://codecov.io/gh/NREL/BuildingMOTIF/branch/main/graph/badge.svg?token=HAFSYH45NX)](https://codecov.io/gh/NREL/BuildingMOTIF) 

The Building Metadata OnTology Interoperability Framework (BuildingMOTIF) is a tool for working with the following semantic data models.

- [ASHRAE 223P](https://www.ashrae.org/about/news/2018/ashrae-s-bacnet-committee-project-haystack-and-brick-schema-collaborating-to-provide-unified-data-semantic-modeling-solution)
- [Brick](https://brickschema.org/)
- [Project Haystack](https://project-haystack.org/)

# Installing
Install [Python >= 3.8.0](https://www.python.org/downloads/).
```
pip install buildingmotif
```

# Using
See the `notebooks` directory. 

# Developing
1. Install [Python >= 3.8.0](https://www.python.org/downloads/).
2. Install [Poetry](https://python-poetry.org/docs/#installation).
3. Clone, download, or fork this repository.

```
poetry install
poetry run pre-commit install
```

## Testing
``` 
poetry run pytest
```
To run tests with DEBUG prints add the `-o log_cli=true` argument to the command

## Formatting
```
poetry run black .
poetry run isort .
poetry run pylama
```

## Documenting
Documentation can be built locally with the following command, which will make the HTML files in the `docs/build/html/` directory.

```
cd docs
poetry run make html
```

## Building and Publishing
```
# build and publish test
poetry publish --build --dry-run

# build and publish
poetry publish --build
```

# Visualizing
![repo-vis](./diagram.svg)
