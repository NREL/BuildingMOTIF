# OSISoft's PI Asset Framework Egress

This library is used to generate an XML file that transposes a BRICK model and a list of automated fault detection and diagnosis (AFDD) rules into an Asset Framework description compatible with OSISoft's PI System.

## Library contents

### afxml.py
This script is inspired by [bsyncpy](https://github.com/BuildingSync/bsyncpy). It translates the XML structure of the Asset Framework XML (AFXML) schema into a Python object that represents the draft XML file and can be edited interactively.
Each AFXML element is defined as a new class, and child elements and enumerations are defined for each element with new classes.
Helper methods allow us to add and modify objects that define the XML elements.
The AFXML schema is proprietary and it is not included in this library. It is available with all installations of OSISoft's PI Systems.

### validation.py
This script uses BuildingMOTIF to validate AFDD rules against a list of requirements for a given building model. The user supplies a JSON file that represents the AFDD rules, and their prerequisites, that they would like to consider for a given BRICK building model. The script translates the JSON file in a series of SPARQL queries, executes those on the BRICK building model, and returns a list of AFDD rules from the JSON file that can be applied to the BRICK building model, if all the requirements for the rule are met. This script also provides a list of failing rules with a reason for failure.

### ttl_to_af.py
This script translates a BRICK model into an XML file that can be imported into an OSISoft PI Asset Framework database. If supplied with a list of AFDD rules, the script will use the validation workflow to also generate AF Analysis for these elements. This allows the automatic configuration of large PI AF databases.

### examples/
In this folder you will find all the files required to generate an AF XML file from a BRICK model and a list of AFDD definitions,

## Public API

This module provides a small, programmatic API for:
- generating a SHACL manifest from AFDD rules expressed in JSON
- validating a BRICK model against those rules (optional, for reporting)
- producing an OSIsoft PI Asset Framework (AF) XML from a BRICK model and rule results

Primary entry points:
- buildingmotif.exports.brick2af.utils.generate_manifest(rules_file: str, output_file: str) -> None
- buildingmotif.exports.brick2af.validation.validate(manifest_ttl: str, model_ttl: str, rule_json: str, output_path: str, format: str) -> None
- buildingmotif.exports.brick2af.validation.apply_rules_to_model(model: buildingmotif.dataclasses.Model, rules: dict) -> dict
- buildingmotif.exports.brick2af.ttl_to_af.Translator
  - add_rules(rulespath: str, validatedpath: str) -> None
  - createAFTree(firstttl: str, outpath: str, merge: Optional[str] = None) -> af.AF

Notes:
- The AF XML schema is proprietary; this code writes an AF-compatible XML using a local copy of the XSD name for reference.
- Validation requires a BRICK model; rules reference BRICK classes and properties.
- You do not need to run OSIsoft tools to generate XML; this module produces the XML file you can import into AF.

## Quickstart (programmatic)

Given:
- a BRICK TTL model at path model.ttl
- an AFDD rules JSON at path rules.json

This snippet validates your model (optional) and generates AF XML suitable for import into OSIsoft PI AF:

```python
import json
from rdflib import Namespace
from buildingmotif.dataclasses import Model, ShapeCollection
from buildingmotif.exports.brick2af.utils import generate_manifest
from buildingmotif.exports.brick2af.validation import validate, apply_rules_to_model
from buildingmotif.exports.brick2af.ttl_to_af import Translator

# Paths
MODEL_TTL = "path/to/model.ttl"
RULES_JSON = "path/to/rules.json"
MANIFEST_TTL = "path/to/manifest.ttl"
VALID_RULES_JSON = "path/to/valid_rules.json"
AF_XML = "path/to/output.xml"

# 1) Generate a SHACL manifest from the JSON rules (optional but recommended)
generate_manifest(RULES_JSON, MANIFEST_TTL)

# 2) (Optional) Validate model against rules; writes a report.{html,md}
#    This step helps you understand which rules pass/fail on your model.
validate(MANIFEST_TTL, MODEL_TTL, RULES_JSON, output_path="report", format="html")

# 3) Compute rule bindings (which rules apply to which resources)
#    Build a BuildingMOTIF Model and parse your BRICK TTL into it
m = Model.create("urn:example:bm")
m.graph.parse(MODEL_TTL, format="turtle")

#    Load rule definitions into memory and compute valid rule bindings
with open(RULES_JSON, "r") as f:
    rules = json.load(f)
valid_rules = apply_rules_to_model(m, rules)

#    Persist valid rule bindings to JSON for the translator
with open(VALID_RULES_JSON, "w") as f:
    json.dump(valid_rules, f)

# 4) Generate the AF XML
translator = Translator()
translator.add_rules(RULES_JSON, VALID_RULES_JSON)
translator.createAFTree(MODEL_TTL, AF_XML)
print(f"Wrote AF XML to: {AF_XML}")
```

## End-to-end using the bundled example

A complete example is provided in examples/ahu-vav-example.py. It demonstrates:
- generating a manifest from JSON rules (examples/GL36_VAV.json)
- validating a sample AHU/VAV BRICK model (examples/g36-combined-ahu-vav.ttl)
- writing a valid_rules.json
- generating AF XML

Run it from this directory:
```bash
python buildingmotif/exports/brick2af/examples/ahu-vav-example.py
```

The script writes:
- GL36_vav_manifest.ttl: SHACL shapes derived from rules
- valid_rules.json: rule bindings computed from the BRICK model
- g36-combined-ahu-vav.xml: AF XML

## API Reference (concise)

- utils.generate_manifest(rules_file, output_file)
  - Input: path to rules JSON; output TTL path
  - Output: writes a SHACL TTL manifest derived from the rules

- validation.validate(manifest_ttl, model_ttl, rule_json, output_path, format)
  - Input: TTL paths to manifest and model; rules JSON path; output base path; "html" or "md"
  - Output: writes report.html or report.md summarizing validation status

- validation.apply_rules_to_model(model, rules) -> dict
  - Input: a BuildingMOTIF Model with your BRICK graph loaded; rules dict loaded from JSON
  - Output: a dict mapping rule URIs to instances that satisfy the rule requirements

- ttl_to_af.Translator
  - add_rules(rulespath, validatedpath)
    - Input: path to source rules JSON; path to valid_rules JSON produced by apply_rules_to_model
  - createAFTree(firstttl, outpath, merge=None)
    - Input: path to BRICK TTL model; output XML path; optional path to merge additional TTL before export
    - Output: writes AF XML; returns an AF object if you need to introspect/extend before writing

## Tips and caveats

- Rule modeling: The rules JSON supports basic constructs like "choice" and nested relationships (hasPoint, hasPart, feeds, etc.).
- Namespaces: Rules reference BRICK terms; your model should use BRICK classes/properties consistent with those rules.
- OSIsoft import: Use OSIsoft tooling to import the produced XML into your AF database. The export/import helpers in ttl_to_af are for testing only.
