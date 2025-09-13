**AF XML Export (brick2af) Using BuildingMOTIF**

- Goal: given a BRICK model and an AFDD rules JSON, generate an OSIsoft PI Asset Framework (AF) XML (.xml) ready for import.
- Audience: backend and web developers integrating a simple export endpoint/UI.

**Prerequisites**
- Python 3.11–3.12 with Poetry and the project installed: `poetry install --with dev`.
- BuildingMOTIF available in-process. For local/dev, an in-memory DB is fine.
- A rules JSON file (see `buildingmotif/exports/brick2af/examples/GL36_VAV.json` for structure).
- A PI AF export configuration JSON (`pi_config.json` with server, database, and units). The translator currently looks for this at a path relative to your working directory. See “PI Config” below.

**Core APIs You Will Use**
- `buildingmotif.exports.brick2af.utils.generate_manifest(rules_file, output_ttl)` and `generate_manifest_from_dict(rules_dict, ns=None)`
- `buildingmotif.exports.brick2af.validation.validate(manifest_ttl, model_ttl, rule_json, output_base, format)`
- `buildingmotif.exports.brick2af.validation.apply_rules_to_model(model, rules_dict)` (object-based)
- `buildingmotif.exports.brick2af.ttl_to_af.Translator`
  - Object-based: `add_rules_from_dict(rules_dict, validated_bindings)` and `create_af_tree_from_model(model, merge_graph=None)`
  - File-based (back-compat): `add_rules(rulespath, validatedpath)` and `createAFTree(model_ttl, af_xml_output, merge=None)`

These mirror the flow shown in `buildingmotif/exports/brick2af/examples/ahu-vav-example.py` but are structured for programmatic use (e.g., in a web handler).

**Minimal End‑to‑End (Programmatic, object-based)**
- Inputs: `MODEL_TTL` (path to your BRICK TTL), and a loaded `rules` dict, both created in-memory.

```python
import json
from rdflib import Graph
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model
from buildingmotif.exports.brick2af.utils import (
    generate_manifest_from_dict,
    xml_dump,
)
from buildingmotif.exports.brick2af.validation import (
    apply_rules_to_model,   # accepts Model or rdflib.Graph
    validate,               # validate(manifest_graph, model, rules, output_base, format)
)
from buildingmotif.exports.brick2af.ttl_to_af import Translator

MODEL_TTL = "/path/to/model.ttl"
RULES_PATH = "/path/to/rules.json"
AF_XML = "/tmp/output_af.xml"

# 0) Ensure a BuildingMOTIF instance (topquadrant requires Java; use "pyshacl" if unavailable)
BuildingMOTIF("sqlite://", shacl_engine="topquadrant")

# 1) Load objects: model graph and rules dict
model_graph = Graph(); model_graph.parse(MODEL_TTL, format="turtle")
rules = json.loads(open(RULES_PATH).read())

# 2) Optional: prepare a base manifest graph (can be empty). validate() will
#    augment it with rule-derived shapes automatically.
manifest_graph = generate_manifest_from_dict(rules)  # or Graph() if you have your own
m = Model.from_graph(model_graph)
validate(manifest_graph, m, rules, "/tmp/report", format="html")

# 3) Compute which rules apply to your model (rule bindings) from compiled graph
compiled = m.compile()
valid_bindings = apply_rules_to_model(compiled.graph, rules)

# 4) Build the AF tree directly from loaded objects (no intermediate files)
tr = Translator()
tr.add_rules_from_dict(rules, valid_bindings)
af_obj = tr.create_af_tree_from_model(m)

# 5) Serialize to XML on disk (if desired)
xml_dump(af_obj, file=AF_XML)
print(f"Wrote AF XML: {AF_XML}")
```

Notes:
- If you prefer a file-based path, `apply_rules_to_model_paths(MODEL_TTL, RULES_JSON)` returns the same `valid_bindings`.
- You can merge additional TTLs (object-based) by calling `create_af_tree_from_model(model, merge_graph=<rdflib.Graph>)` after adding the extra graph to `merge_graph`.

**Optional Validation + Report (objects)**
To generate a quick pass/fail report across all rules for a model using in-memory graphs and rules dict:

```python
from rdflib import Graph
from buildingmotif.exports.brick2af.utils import generate_manifest_from_dict
from buildingmotif.exports.brick2af.validation import validate

model_graph = Graph(); model_graph.parse(MODEL_TTL, format="turtle")
rules = json.loads(open(RULES_PATH).read())
manifest_graph = generate_manifest_from_dict(rules)
m = Model.from_graph(model_graph)
validate(manifest_graph, m, rules, "/tmp/validation_report", format="html")
```

This writes an HTML (or MD) report summarizing which rules pass/fail and why.

**PI Config (Required)**
The AF translator reads a `pi_config.json` file for server/database and unit mappings (UOM to AF attribute metadata). A sample lives at `buildingmotif/exports/brick2af/pi_config.json`. The current translator looks for `../pi_config.json` relative to the working directory you run from. Ensure one of the following:
- Run your code from a directory where `../pi_config.json` resolves to the sample config above (e.g., `cd buildingmotif/exports/brick2af/examples`), or
- Provide a copy of `pi_config.json` at a path that matches `../pi_config.json` relative to your process CWD, or
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
    // ... additional unit mappings
  }
}
```

Only the `units` mapping and DB identifiers are used for XML construction; the import/export executables are not invoked by the export flow itself.

**Integrating in a Web Frontend (object-based)**

High‑level flow for a POST `/export-afxml` endpoint:
- Inputs from client:
  - `model_ttl` (path or uploaded file you save to a temp path), and
  - `rules_json` (path or JSON body uploaded by the client).
- Backend steps:
  - Ensure a BuildingMOTIF instance (instantiate once per process).
  - If rules are in-memory JSON, compute bindings via `apply_rules_to_model(Model.from_file(model_ttl), rules_dict)`; otherwise, `apply_rules_to_model_paths`.
  - Create `Translator()`, call `add_rules_from_dict(rules_dict, valid_bindings)`.
  - Call `create_af_tree_from_model(model)`.
  - Serialize with `xml_dump(af_obj, file=...)` or return `str(af_obj).encode("utf-8")` as the response body.
  - Return the XML as a file download or object storage URL.

Example (pseudo‑handler):
```python
def export_afxml(model_ttl_path: str, rules: dict) -> bytes:
    from tempfile import NamedTemporaryFile
    from buildingmotif import BuildingMOTIF
    from buildingmotif.dataclasses import Model
    from buildingmotif.exports.brick2af.validation import apply_rules_to_model
    from buildingmotif.exports.brick2af.ttl_to_af import Translator
    from buildingmotif.exports.brick2af.utils import xml_dump

    BuildingMOTIF("sqlite://", shacl_engine="pyshacl")  # safer for server envs without Java

    # Compute valid rule bindings
    model = Model.from_file(model_ttl_path)
    valid = apply_rules_to_model(model, rules)

    # Translate to AF XML from loaded objects
    tr = Translator()
    tr.add_rules_from_dict(rules, valid)
    af_obj = tr.create_af_tree_from_model(model)
    # Return bytes for direct download; alternatively, xml_dump to a temp file
    return str(af_obj).encode("utf-8")
```

Implementation tips:
- Use the object-based methods (`add_rules_from_dict`, `create_af_tree_from_model`) to avoid writing temp files.
- If your deployment won’t have Java, set `shacl_engine="pyshacl"` when creating the BuildingMOTIF singleton.
- Make sure `pi_config.json` is discoverable at runtime as described earlier.

**Troubleshooting**
- “Cannot find pi_config.json”: ensure the config is present at a path that resolves to `../pi_config.json` from your process CWD, or adjust your CWD.
- Empty AF XML or missing attributes: confirm your `units` mapping in `pi_config.json` covers the BRICK units present in your model.
- Validation failures: run the optional `validate` flow to get a human‑readable report and adjust rules/model accordingly.
