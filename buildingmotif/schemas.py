from typing import Any

import jsonschema

LIBRARIES_YAML_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "oneOf": [
            {
                "type": "object",
                "properties": {"directory": {"type": "string"}},
                "required": ["directory"],
            },
            {
                "type": "object",
                "properties": {"ontology": {"type": "string"}},
                "required": ["ontology"],
            },
            {
                "type": "object",
                "properties": {
                    "git": {
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string"},
                            "branch": {"type": "string"},
                            "path": {"type": "string"},
                        },
                        "required": ["repo", "branch", "path"],
                    }
                },
                "required": ["git"],
            },
        ],
    },
}


def validate_libraries_yaml(doc: Any):
    """
    Validates a given document against the library.yml schema. Raises
    a jsonschema.exceptions.ValidationError if errors are found

    :param doc: a value retrieved from deserializing libraries.yml file
    """
    jsonschema.validate(schema=LIBRARIES_YAML_SCHEMA, instance=doc)
