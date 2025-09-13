import json

from buildingmotif import BuildingMOTIF
from buildingmotif.exports.brick2af.ttl_to_af import Translator
from buildingmotif.exports.brick2af.utils import generate_manifest
from buildingmotif.exports.brick2af.validation import (
    apply_rules_to_model_paths,
    validate,
)

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

# Validate the model against the rules (u lil' punk). Generate an HTML report.
validate(outmanifest, inttl, injson, outreport, reportformat)

print(injson, "rules have been validated against", inttl)
# Output an XML file that can be loaded in OSISoft PI Asset Explorer
validrules = apply_rules_to_model_paths(inttl, injson)
with open(outrules, "w") as f:
    json.dump(validrules, f)
translator = Translator()
translator.add_rules(injson, outrules)
translator.createAFTree(inttl, outxml)
