# Representing an XML Schema in Python

The purpose of the `afxml.py` file is to make it more robust to create XML files that follow the Asset Framework XML Schema, 2015 (AFXML). The file contains functions to parse and validate XML documents against the AFXML schema. It also includes classes for representing an asset in the AFXML format.

## Elements as Classes

Each element of the AFXML Schema is represented as a Python data class, such as `AFElement`, `AFAttribute`, `AFAnalysis`, `Unit`, etc.

```python
class AFPlugIn(PIAFElement):
    element_type = "xs:string"
    element_enumerations = []
```
We restrict an element to a certain type by using the `element_type` and `element_enumerations`.

```python
class AFExtendedProperty(PIAFElement):
    pass
AFExtendedProperty.element_children = [
    ("id", id),
    ("Name", Name),
    ("Type", Type),
    ("Value", Value),
]
```
We specify valid child elements by populating the `element_children` list with 2-tuples such as `(element-name, element-reference)` where `element-reference` should be a valid class defined in `afxml.py`. 

```python
class Value(PIAFElement):
    element_type = "xs:any"

Value.element_attributes = ["default", "type"]
```

Likewise, we can restrict elements to certain attributes by providing the attribute names in a plain text `element_attributes` list.
The library is written such that `element_children` and `element_attributes` should be configured after an element's class has been declared, and not within the class declaration.

## Utilities

The base class used for all other classes in this library is called `PIAFElement` and it contains methods for setting and getting class attributes, for validating data types and data structures, and for serializing the model.