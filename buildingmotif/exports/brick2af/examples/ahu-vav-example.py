import json
import sys

sys.path.append("..")
from ttl_to_af import Translator
from utils import generate_manifest
from validation import apply_rules_to_model, validate

inttl = "g36-combined-ahu-vav.ttl"
injson = "GL36_VAV.json"
outmanifest = "GL36_vav_manifest.ttl"
outxml = "g36-combined-ahu-vav.xml"
outrules = "valid_rules.json"
reportformat = "html"

# Generate a manifest file from the JSON rules
generate_manifest(injson, outmanifest)

# Validate the model against the rules (u lil' punk). Generate an HTML report.
validate(outmanifest, inttl, injson, outxml, reportformat)

# Output an XML file that can be loaded in OSISoft PI Asset Explorer
validrules = apply_rules_to_model(inttl, injson)
with open(outrules, "w") as f:
    json.dump(validrules, f)
translator = Translator()
translator.add_rules(injson, outrules)
translator.createAFTree(inttl, outxml)
