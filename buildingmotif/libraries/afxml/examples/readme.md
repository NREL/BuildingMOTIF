# Usage

### Prerequisites
You must have:
- a Turtle (TTL) file that represents a building using the [BRICK](http://brickschema.org) ontology
- a JSON file that lists AFDD rules to be considered for this building model.
Below, we explain what these are.

### The TTL model

We are using one of the models provided in the [BRICK schema repository](https://github.com/BrickSchema/Brick/tree/master/examples/g36) on GitHub, `g36-combined-ahu-vav.ttl'. That model is a simple AHU with VAV terminal. 

### The JSON rules dictionary

The rules dictionary is a nested dictionary. For each new rule, a new dictionary entry should be added to the main dictionary. Let us break an example down for comprehension. The rule below verifies the availability of points in the equipment schedule, in order to apply other AFDD rules later on.

```json
"G36FCU_SAT_POINTS" : {
        "name" : "Guideline 36 - All supply air temperature control points and sensors are available for AFDD",
        "aftype" : "analysis",
        "aftimerule" : "Periodic",
        "frequency" : 900,
        "applicability" : ["FCU"],
        "dependencies": [],
        "definitions": {
            "Supply_Air_temperature_Sensor": {
                "choice": [
                    {"hasPoint": "Supply_Air_Temperature_Sensor"},
                    {"hasPoint": "Zone_Air_Temperature_Sensor"}
                ]
                },
            "Supply_Air_Temperature_Setpoint": {
                "choice": [
                    {"hasPoint": "Supply_Air_Temperature_Setpoint"},
                    {"hasPoint": "Zone_Air_Temperature_Setpoint"}
                ]
            }
        },
        "output" : "Supply_Air_Temperature_Average = Avg(Supply_Air_temperature_Sensor); Supply_Air_Temperature_Error_Threshold = 3.0;"
    }
```
    
The entry key is the machine-readable rule name, `G36FCU_SAT_POINTS`, and its elements are:
    - name: the human-readable name that will appear in the validation
    - aftype, aftimerule, frequency, output: OSISoft PI specific. Please refer to PI Asset Framework's manual.
    - applicability: list of strings that match existing BRICK types. The rule is only applied to these BRICK types.
    - dependencies: key value of another rule in the high-level dictionary. If a rule depends on requisites defined in other rules, you can refer to that other rule directly. The new rule's requirements will be inherited from the keys defined in "dependencies".
    - definitions: TODO.

In this example, the `G36FCU_SAT_POINTS` rule requires that all `FCUs` be checked for the following points:
- a supply air temperature sensor, which could be represented as either a `supply` or a `zone air temperature sensor`
- a supply air temperature setpoint, which could be represented as either a `supply` or a `zone air temperature setpoint`
It defines no dependencies on other rules, and the OSISoft PI fields are completed with some PI-specific data.
TODO: expand the library to output the rule in an interoperable format, and not only something compatible with the AFXML schema.

### Running the example

Use the ahu-vav-example.py script: `python ahu-vav-example.py`.
This script does the following:
1) it loads the rules JSON file and generates a manifest from it. The manifest contains shape definitions that we'll later use to execute queries on the model.
2) it verifies the TTL model against those rules
3) it generates an HTML or MD report on the applicability of each rule, and provides debug messages for each failure
4) it generates an XML file that represents the model and all _valid_ rules in a format that can imported directly into a PI Systems Asset Framework
