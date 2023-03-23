# Ingresses

*Ingresses* are BuildingMOTIF's mechanism for importing metadata from external sources.
The `Ingress` APIs are deliberately general so that they can be easily extended to new metadata sources.

`IngressHandler` has two abstract subclasses:
- [`RecordIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.base.html#buildingmotif.ingresses.base.RecordIngressHandler), which produces `Record`s
- [`GraphIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.base.html#buildingmotif.ingresses.base.GraphIngressHandler), which produces `Graph`s

Every concrete `IngressHandler` should inherit from one of these two classes.

## Ingress Types

### Record Ingress Handler

[`RecordIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.base.html#buildingmotif.ingresses.base.RecordIngressHandler) defines one method: `records() -> List[Record]`.

A `Record` is a simple Python data structure:

```python
@dataclass
class Record:
    # a "type hint" or other identifier for an application-defined category of Records
    rtype: str
    # key-value pairs of data from the underlying source. Application-defined structure
    fields: dict
```

The choice of values for the `Record` is up to each `RecordIngressHandler` instance:
- the [`BACnetIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.bacnet.html#buildingmotif.ingresses.bacnet.BACnetNetwork) uses the `rtype` field to differentiate between BACnet Devices and BACnet Objects. The `fields` field contains key-value pairs of different BACnet properties like `name` and `units`
- the [`CSVIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.csv.html#buildingmotif.ingresses.csv.CSVIngress) uses the `rtype` field to denote the CSV filename, and uses the `fields` field to store column-cell values from each row of the CSV file

### Graph Ingress Handler

[`GraphIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.base.html#buildingmotif.ingresses.base.GraphIngressHandler) defines one method: `graph(ns: rdflib.Namespace) -> rdflib.Graph`.

The `rdflib.Graph` returned by this method contains RDF data (inferred, translated, computed, etc) from some underlying source.
`GraphIngressHandler`s source their metadata from either an upstream `RecordIngressHandler` or any other source provided in the instantiation of the `GraphIngressHandler` subclass.

Any new entities/URIs/etc created or inferred by the `GraphIngressHandler` should be placed into the provided namespace (`ns`).
An instance of `GraphIngressHandler` is typically at the *end* of a pipeline of `IngressHandler`s.

## Useful Built-in Ingress Handlers

BuildingMOTIF provides several built-in ingress handlers.
The full list can be found [here](/reference/apidoc/_autosummary/buildingmotif.ingresses.html).

### BACnet Networks

The [`BACnetIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.bacnet.html#buildingmotif.ingresses.bacnet.BACnetNetwork) takes an IP subnet as an argument (e.g. `10.0.0.1/24`) and generates a set of `Record`s corresponding to the BACnet devices and objects found on that subnet.

- `rtype`: "object" if the `Record` represents a BACnet Object, else "device" if the `Record` represents a BACnet Device
- `fields`: key-value pairs that differ based on `rtype`:
    - BACnet devices: `address` and `device_id` for BACnet devices
    - BACnet objects: `device_id` (for owning BACnet device) and all properties on the object

### CSV Files

The [`CSVIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.csv.html#buildingmotif.ingresses.csv.CSVIngress) takes a CSV filename as an argument  (e.g. `mydata.csv`) and generates a set of `Record`s corresponding to each row in the file.

- `rtype`: the filename that contained the row
- `fields`: key-value pairs for the row. The key is the column name; the value is the value of that column at the given row

### XLSX / Spreadsheet Files

The [`XLSXIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.xlsx.html#buildingmotif.ingresses.xlsx.XLSXIngress) takes a path to an `.xlsx` file as an argument and generates a set of `Records` for each row for each sheet in the spreadsheet file.

- `rtype`: the sheet name containing the row
- `fields`: key-value pairs for each row; the keys are the names of the columns and the values are the cell values at that column for the given row

### Template Instantiation

The [`TemplateIngress`](/reference/apidoc/_autosummary/buildingmotif.ingresses.template.html#buildingmotif.ingresses.template.TemplateIngress) class instantiates a given `Template` with each of the `Record`s generated by an upstream `RecordIngressHandler`. Instantiating `TemplateIngress`  requires a [`Template`](/reference/apidoc/_autosummary/buildingmotif.dataclasses.template.html#buildingmotif.dataclasses.template.Template) instance (probably from a `Library`), an optional "mapper", and an upstream `RecordIngressHandler`.

A "mapper" is a function which maps the column names of the CSV file to the parameters of a template.
If "mapper" is left as `None`, then the `TemplateIngress` will use the column names as the parameter names.

There is also a [`TemplateIngressWithChooser`](/reference/apidoc/_autosummary/buildingmotif.ingresses.template.html#buildingmotif.ingresses.template.TemplateIngressWithChooser) class which acts essentially the same as `TemplateIngress`, but uses an additional function to dynamically choose the `Template` to be instantiated for each `Record`.

## Examples

### BACnet to Brick

See [the BACnet to Brick guide](/guides/bacnet-to-brick)

### CSV Import

Assume we have the following CSV file:

```
name,room,name-co2,name-temp,name-sp
tstat2,room345,co2-345,temp-345,sp-345
tstat3,room567,cow-567,temp-567,sp-567
```

And the following Template in a library called `csv-tutorial`:

```yml
my-thermostat:
  body: >
    @prefix P: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    P:name a brick:Thermostat ;
        brick:hasLocation P:room .
  dependencies:
  - template: https://brickschema.org/schema/Brick#Room
    library: https://brickschema.org/schema/1.3/Brick
    args: {"name": "room"}
  - template: my-tstat-points
    args: {"name": "name"}
    
my-tstat-points:
  body: >
    @prefix P: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    P:name a brick:Thermostat ;
        brick:hasPoint P:temp, P:sp, P:co2 .
  dependencies:
    - template: https://brickschema.org/schema/Brick#Temperature_Sensor
      library: https://brickschema.org/schema/1.3/Brick
      args: {"name": "temp"}
    - template: https://brickschema.org/schema/Brick#Temperature_Setpoint
      library: https://brickschema.org/schema/1.3/Brick
      args: {"name": "sp"}
    - template: https://brickschema.org/schema/Brick#CO2_Sensor
      library: https://brickschema.org/schema/1.3/Brick
      args: {"name": "co2"}
```

We can create a CSV ingress handler using the built-in class ([`CSVIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.csv.html#buildingmotif.ingresses.csv.CSVIngress)):

```python
from rdflib import Namespace, Graph
from buildingmotif import BuildingMOTIF
from buildingmotif.namespaces import BRICK
from buildingmotif.dataclasses import Model, Library, Template
from buildingmotif.ingresses import CSVIngress, TemplateIngress, Record

bm = BuildingMOTIF("sqlite://") # in-memory
BLDG = Namespace("urn:my_site/")
model = Model.create(BLDG) # create our model
lib = Library.load(directory="csv-tutorial") # load in the library containing our template

csv = CSVIngress("data.csv") # the CSV file above
ingress = TemplateIngress(tstat_templ.inline_dependencies(), None, csv)
graph = ingress.graph(BLDG)
print(graph.serialize()) # print the resulting model
```

The `None` on the final line of the cell above is the "mapper".