import json

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model
from buildingmotif.exports.brick2af.ttl_to_af import Translator
from buildingmotif.exports.brick2af.utils import generate_manifest, xml_dump
from buildingmotif.exports.brick2af.validation import apply_rules_to_model, validate

inttl = "g36-combined-ahu-vav.ttl"
injson = "GL36_VAV.json"
outmanifest = "GL36_vav_manifest.ttl"
outxml = "g36-combined-ahu-vav.xml"
outrules = "valid_rules.json"
outreport = "g36-combined-ahu-vav"
reportformat = "html"

# Ensure a BuildingMOTIF instance exists (in-memory DB for local runs)
BuildingMOTIF("sqlite://", shacl_engine="topquadrant")

# Generate a manifest file from the JSON rules
generate_manifest(injson, outmanifest)

# Validate the model against the rules (optional). Generate an HTML report.
validate(outmanifest, inttl, injson, outreport, reportformat)

print(injson, "rules have been validated against", inttl)

# Object-only flow: load objects, compute bindings, pass them directly
rules = json.load(open(injson))
m = Model.from_file(inttl)
validrules = apply_rules_to_model(m, rules)

translator = Translator()
translator.add_rules_from_dict(rules, validrules)
af_obj = translator.create_af_tree_from_model(m)

# Serialize AF XML to disk
xml_dump(af_obj, file=outxml)
print("Wrote AF XML:", outxml)
