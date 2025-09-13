**AF XML Export (brick2af) Using BuildingMOTIF**

- Goal: given a BRICK model and an AFDD rules JSON, generate an OSIsoft PI Asset Framework (AF) XML (.xml) ready for import.
- Audience: backend and web developers integrating a simple export endpoint/UI.

Prerequisites
- Python 3.11–3.12 with Poetry and the project installed: `poetry install --with dev`.
- BuildingMOTIF available in-process. For local/dev, an in-memory DB is fine.
- A rules JSON file (see `buildingmotif/exports/brick2af/examples/GL36_VAV.json` for structure).
- A PI AF export configuration JSON (`pi_config.json` with server, database, and units). The translator currently looks for this at a path relative to your working directory. See “PI Config” below.

Core APIs You Will Use
- buildingmotif.exports.brick2af.utils.generate_manifest(rules_dict, ns=None) → rdflib.Graph
- buildingmotif.exports.brick2af.validation.validate(manifest_graph_or_path, model, rules_dict_or_path, output_base, format)
- buildingmotif.exports.brick2af.validation.apply_rules_to_model(model, rules_dict)
- buildingmotif.exports.brick2af.validation.apply_rules_to_model_paths(model_ttl_path, rules_json_path)
- buildingmotif.exports.brick2af.ttl_to_af.Translator
  - add_rules(rules_json_path, validated_bindings_json_path)
  - createAFTree(model_ttl_path, af_xml_output_path, merge=None)

Minimal End‑to‑End (file-based)
Inputs: MODEL_TTL (path to your BRICK TTL), RULES_JSON (path to rules JSON). This flow uses only existing functions.

```python
import json
from tempfile import NamedTemporaryFile
from rdflib import Graph
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model
from buildingmotif.exports.brick2af.utils import generate_manifest
from buildingmotif.exports.brick2af.validation import (
    apply_rules_to_model_paths,
    validate,
)
from buildingmotif.exports.brick2af.ttl_to_af import Translator

MODEL_TTL = "/path/to/model.ttl"
RULES_PATH = "/path/to/rules.json"
AF_XML = "/tmp/output_af.xml"

# 0) Ensure a BuildingMOTIF instance (topquadrant requires Java; use "pyshacl" if unavailable)
BuildingMOTIF("sqlite://", shacl_engine="pyshacl")

# 1) Optional validation report (build a manifest graph from rules)
rules_dict = json.loads(open(RULES_PATH).read())
manifest_graph = generate_manifest(rules_dict)
model = Model.from_file(MODEL_TTL)
validate(manifest_graph, model, rules_dict, "/tmp/validation_report", format="html")

# 2) Compute rule bindings (which rules apply to the model)
bindings = apply_rules_to_model_paths(MODEL_TTL, RULES_PATH)

# 3) Write bindings to a JSON file the Translator can consume (stringify keys/values)
def stringify_bindings(b):
    out = {}
    for rule_uri, focus_map in b.items():
        rule_uri_s = str(rule_uri)
        out.setdefault(rule_uri_s, {})
        for focus_node, vars_map in focus_map.items():
            out[rule_uri_s][str(focus_node)] = {str(k): str(v) for k, v in vars_map.items()}
    return out

bindings_json = stringify_bindings(bindings)
with NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
    VALIDATED_PATH = tmp.name
    json.dump(bindings_json, tmp, indent=2)

# 4) Build AF XML using file-based translator APIs
tr = Translator()
tr.add_rules(RULES_PATH, VALIDATED_PATH)
tr.createAFTree(MODEL_TTL, AF_XML)
print(f"Wrote AF XML: {AF_XML}")
```

Optional: Merge additional TTLs
Pass a single extra TTL path or a list of TTL paths as the merge parameter to createAFTree:
- tr.createAFTree(MODEL_TTL, AF_XML, merge="/path/to/extra.ttl")
- tr.createAFTree(MODEL_TTL, AF_XML, merge=["/path/a.ttl", "/path/b.ttl"])

Optional Validation + Report (objects)
To generate a quick pass/fail report across all rules for a model using in-memory graphs and rules dict:

```python
import json
from rdflib import Graph
from buildingmotif.dataclasses import Model
from buildingmotif.exports.brick2af.utils import generate_manifest
from buildingmotif.exports.brick2af.validation import validate

MODEL_TTL = "/path/to/model.ttl"
RULES_PATH = "/path/to/rules.json"

rules = json.loads(open(RULES_PATH).read())
manifest_graph = generate_manifest(rules)
model = Model.from_file(MODEL_TTL)
validate(manifest_graph, model, rules, "/tmp/validation_report", format="html")
```

PI Config (Required)
The AF translator reads a pi_config.json file for server/database and unit mappings (UOM to AF attribute metadata). A sample lives at buildingmotif/exports/brick2af/pi_config.json. The current translator looks for ../pi_config.json relative to the working directory you run from. Ensure one of the following:
- Run your code from a directory where ../pi_config.json resolves to the sample config above (e.g., cd buildingmotif/exports/brick2af/examples), or
- Provide a copy of pi_config.json at a path that matches ../pi_config.json relative to your process CWD, or
- Adjust your runtime CWD accordingly.

The config must contain:
```json
{
  "server": "your-pi-server-name",
  "database": "your-database-name",
  "piexportpath": "C:\\Program Files\\PIPC\\AF\\AFExport.exe",
  "piimportpath": "C:\\Program Files\\PIPC\\AF\\AFImport.exe",
  "units": {
    "DEG_F": {"uom": "°F", "aftype": "Int32", "value": ""}
  }
}
```
Only the units mapping and DB identifiers are used for XML construction; the import/export executables are not invoked by the export flow itself.

Integrating in a Web Backend (file-based)
High‑level flow for a POST /export-afxml endpoint:
- Inputs from client:
  - model_ttl (path or uploaded file you save to a temp path)
  - rules_json (path or JSON body uploaded by the client)
- Backend steps:
  - Ensure a BuildingMOTIF instance (instantiate once per process).
  - Compute bindings via apply_rules_to_model_paths(model_ttl, rules_json_path) and write a stringified JSON as shown above.
  - Create Translator(), call add_rules(rules_json_path, validated_bindings_json_path).
  - Call createAFTree(model_ttl, output_xml_path).
  - Return the XML as a file download or object storage URL.

Troubleshooting
- “Cannot find pi_config.json”: ensure the config is present at a path that resolves to ../pi_config.json from your process CWD, or adjust your CWD.
- Empty AF XML or missing attributes: confirm your units mapping in pi_config.json covers the BRICK units present in your model.
- Validation failures: run the optional validate flow to get a human‑readable report and adjust rules/model accordingly.
