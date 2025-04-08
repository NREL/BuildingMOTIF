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