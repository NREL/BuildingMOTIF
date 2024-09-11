# Point Label Parsing

The purpose of this explanation is to describe the framework for defining point label parsing rules and provide examples of how to use it.

One common source of building metadata are the "point labels" used in building management systems to label or tag the input and output data points with some human-readable description.
It is often useful to extract structured information from these labels to help with constructing a semantic model of the building.

BuildingMOTIF provides a framework for defining point label naming conventions and parsing them into structured data.
The output of this process is a set of typed <a href="../reference/apidoc/_autosummary/buildingmotif.label_parsing.html#buildingmotif.label_parsing.Token">Token</a> objects that can be input into a "Semantic Graph Synthesis" process to generate a semantic model of the building.

```{admonition} Semantic Graph Synthesis
This feature is coming soon! This label parsing framework is just part of the larger BuildingMOTIF toolkit for generating semantic models of buildings.
```

## Background

The point label parsing framework in BuildingMOTIF is based on the concept of "parser combinators".
Parser combinators are a way of defining parsers by combining smaller parsers together.
In BuildingMOTIF, the "combinators" are defined as Python functions that take a string as input and return a list of <a href="../reference/apidoc/_autosummary/buildingmotif.label_parsing.html#buildingmotif.label_parsing.TokenResult">TokenResult</a>s.
These combinators can be combined together to create more complex parsers.


Here is a short example:

```python
def parse_ahu_label(label: str) -> List[TokenResult]:
    return sequence(
        string("AHU", Constant(BRICK.Air_Handling_Unit)),
        string("-", Delimiter),
        regex(r"\d+", Identifier)
    )(label)
```

This defines a parser which matches strings like "AHU-1" or "AHU-237" and returns a list of `Token`s.
The `sequence` combinator combines the three parsers together, and the `string` and `regex` combinators match specific strings or regular expressions.

Using parser combinators in this way allows you to define complex parsing rules in a concise and readable way.

The example output of the `parse_ahu_label` function might look like this:

```python
parse_ahu_label("AHU-1")
# [TokenResult(value='AHU', token=Constant(value=rdflib.term.URIRef('https://brickschema.org/schema/Brick#Air_Handling_Unit')), length=3, error=None, id=None), 
# TokenResult(value='-', token=Delimiter(value='-'), length=1, error=None, id=None),
# TokenResult(value='1', token=Identifier(value='1'), length=1, error=None, id=None)]

parse_ahu_label("AH-1")
# [TokenResult(value=None, token=Null(value=None), length=0, error='Expected AHU, got AH-', id=None)]
```

## BuildingMOTIF Parser Combinators

The `buildingmotif.label_parsing.combinators` module provides a set of parser combinators for defining point label parsing rules.
Here are some of the most commonly used combinators:

- `string`: Matches a specific string and returns a `Token` with a constant value.
- `regex`: Matches a regular expression and returns a `Token` with the matched value.
- `choice`: Matches one of a list of parsers. Uses the first one that matches.
- `sequence`: Matches a sequence of parsers and returns a list of `Token`s.
- `constant`: Returns a `Token` with a constant value. Does not consume any input.
- `many`: Matches zero or more occurrences of a parser.
- `maybe`: Matches zero or one occurrence of a parser.
- `until`: Matches a parser until another parser is matched.


### Defining New Combinators

These are all just Python functions, so you can define your own combinators as needed.

```python
delimiters = regex(r"[._:/\- ]", Delimiter)
identifier = regex(r"[a-zA-Z0-9]+", Identifier)
named_equip = sequence(equip_abbreviations, maybe(delimiters), identifier)
named_point = sequence(point_abbreviations, maybe(delimiters), identifier)
```

More generally, a combinator is any function which takes a string as input and returns a list of `TokenResult`s.
The methods above (`regex`, `sequence`, `delimiters`) are functions which *return* a combinator as an argument.

### Abbreviations

Abbreviations are a common feature of point labels.
Strings like "AHU" for "Air Handling Unit" or "VAV" for "Variable Air Volume" are often used to save space on labels.
You can use the `abbreviations` combinator to define a set of abbreviations and automatically expand them in the input string.

We can define a dictionary of abbreviations like this:

```python
my_abbreviations = {
    "AHU": BRICK.Air_Handling_Unit,
    "FCU": BRICK.Fan_Coil_Unit,
    "VAV": BRICK.Variable_Air_Volume_Box,
    "CRAC": BRICK.Computer_Room_Air_Conditioner,
    "HX": BRICK.Heat_Exchanger,
    "PMP": BRICK.Pump,
    "RVAV": BRICK.Variable_Air_Volume_Box_With_Reheat,
    "HP": BRICK.Heat_Pump,
    "RTU": BRICK.Rooftop_Unit,
    "DMP": BRICK.Damper,
    "STS": BRICK.Status,
    "VLV": BRICK.Valve,
    "CHVLV": BRICK.Chilled_Water_Valve,
    "HWVLV": BRICK.Hot_Water_Valve,
    "VFD": BRICK.Variable_Frequency_Drive,
    "CT": BRICK.Cooling_Tower,
    "MAU": BRICK.Makeup_Air_Unit,
    "R": BRICK.Room,
}

my_abbreviations_parser = abbreviations(my_abbreviations)
```

Then we can use `my_abbreviations_parser` in our label parsing rules to automatically expand abbreviations.
Note how the key of the `my_abbreviations` dictionary is the abbreviation and the value is the RDF Brick class that the abbreviation expands to.

To expand our earlier example to work for other abbreviations, we can rewrite the parser like this:

```python
def parse_label(label: str) -> List[TokenResult]:
    return sequence(
        my_abbreviations_parser,
        string("-", Delimiter),
        regex(r"\d+", Identifier)
    )(label)

parse_label("AHU-1")
# [TokenResult(value='AHU', token=Constant(value=rdflib.term.URIRef('https://brickschema.org/schema/Brick#Air_Handling_Unit')), length=3, error=None, id=None),
# TokenResult(value='-', token=Delimiter(value='-'), length=1, error=None, id=None),
# TokenResult(value='1', token=Identifier(value='1'), length=1, error=None, id=None)]

parse_label("FCU-1")
# [TokenResult(value='FCU', token=Constant(value=rdflib.term.URIRef('https://brickschema.org/schema/Brick#Fan_Coil_Unit')), length=3, error=None, id=None),
# TokenResult(value='-', token=Delimiter(value='-'), length=1, error=None, id=None),
# TokenResult(value='123', token=Identifier(value='123'), length=3, error=None, id=None)]

parse_label("AH-1")
# [TokenResult(value=None, token=Null(value=None), length=0, error='Expected
# AHU, got AH- | Expected FCU, got AH- | Expected VAV, got AH- | Expected CRAC,
# got AH-3 | Expected HX, got AH | Expected PMP, got AH- | Expected RVAV, got
# AH-3 | Expected HP, got AH | Expected RTU, got AH- | Expected DMP, got AH- |
# Expected STS, got AH- | Expected VLV, got AH- | Expected CHVLV, got AH-3 |
# Expected HWVLV, got AH-3 | Expected VFD, got AH- | Expected CT, got AH |
# Expected MAU, got AH- | Expected R, got A', id=None)]
```

### Error Handling

The parser combinators in BuildingMOTIF provide detailed error messages when a parsing rule fails.
This can be useful for debugging and understanding why a particular label did not match the expected format.
The error messages include information about what was expected and what was found in the input string.

If any `TokenResult` in the list has an `error` field, it means that the parsing rule failed at that point.

## Example

Consider these point labels:

```
:BuildingName_02:FCU503_ChwVlvPos
:BuildingName_02:FCU510_EffOcc
:BuildingName_02:FCU507_UnoccHtgSpt
:BuildingName_02:FCU415_UnoccHtgSpt
:BuildingName_01:FCU203_OccClgSpt
:BuildingName_02:FCU529_UnoccHtgSpt
:BuildingName_01:FCU243_EffOcc
:BuildingName_01:FCU362_ChwVlvPos
```

We can define a set of parsing rules to extract structured data from these labels.
This is essentially just an expression of the building point naming convention.

```python
equip_abbreviations = abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK)
# define our own for Points (specific to this building)
point_abbreviations = abbreviations({
    "ChwVlvPos": BRICK.Position_Sensor,
    "HwVlvPos": BRICK.Position_Sensor,
    "RoomTmp": BRICK.Air_Temperature_Sensor,
    "Room_RH": BRICK.Relative_Humidity_Sensor,
    "UnoccHtgSpt": BRICK.Unoccupied_Air_Temperature_Heating_Setpoint,
    "OccHtgSpt": BRICK.Occupied_Air_Temperature_Heating_Setpoint,
    "UnoccClgSpt": BRICK.Unoccupied_Air_Temperature_Cooling_Setpoint,
    "OccClgSpt": BRICK.Occupied_Air_Temperature_Cooling_Setpoint,
    "SaTmp": BRICK.Supply_Air_Temperature_Sensor,
    "OccCmd": BRICK.Occupancy_Command,
    "EffOcc": BRICK.Occupancy_Status,
})

def custom_parser(target):
    return sequence(
        string(":", Delimiter),
        # regex until the underscore
        constant(Constant(BRICK.Building)),
        regex(r"[^_]+", Identifier),
        string("_", Delimiter),
        # number for AHU name
        constant(Constant(BRICK.Air_Handling_Unit)),
        regex(r"[0-9a-zA-Z]+", Identifier),
        string(":", Delimiter),
        # equipment types
        equip_abbreviations,
        # equipment ident
        regex(r"[0-9a-zA-Z]+", Identifier),
        string("_", Delimiter),
        maybe(
            sequence(regex(r"[A-Z]+[0-9]+", Identifier), string("_", Delimiter)),
        ),
        # point types
        point_abbreviations,
    )(target)
```
