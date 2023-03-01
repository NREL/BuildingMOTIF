import pytest
from jsonschema.exceptions import ValidationError

from buildingmotif.schemas import validate_libraries_yaml

bad_fixtures = [
    {"ontology": "Brick.ttl"},  # needs to be outer array
    {"abc": "def"},  # needs to be outer array
    [{"abc": "def"}],  # bad key
    [{"git": {"repo": "abc"}}],  # missing fields
    [{"directory": 123}],  # bad data type
    [{"directory": 123}, {"directory": "/a/b/c"}],  # one bad field one good field
    [{"ontology": "Brick.ttl", "directory": "a/b/c"}],  # only one field at a time
]

good_fixtures = [
    [{"ontology": "Brick.ttl"}],
    [{"directory": "a/b/c"}],
    [{"git": {"repo": "https://abc", "branch": "main", "path": "my/templates"}}],
    [{"ontology": "Brick.ttl"}, {"directory": "a/b/c"}],
]


def pytest_generate_tests(metafunc):
    if "bad_fixture" in metafunc.fixturenames:
        metafunc.parametrize("bad_fixture", bad_fixtures)
    if "good_fixture" in metafunc.fixturenames:
        metafunc.parametrize("good_fixture", good_fixtures)


def test_libraries_yml_schema_invalidate_bad(bad_fixture):
    with pytest.raises(ValidationError):
        validate_libraries_yaml(bad_fixture)


def test_libraries_yml_schema_validate_good(good_fixture):
    validate_libraries_yaml(good_fixture)
