# OSISoft's PI Asset Framework Egress

This library is used to generate an XML file that transposes a BRICK model and a list of automated fault detection and diagnosis (AFDD) rules into an Asset Framework description compatible with OSISoft's PI System.

## Library contents

### An example
This example demonstrates how to use BuildingMOTIF to configure a PI Server instance and enable certain applications such as automatic fault detection and diagnosis, building monitoring, and other labor-intensive tasks that can be automated with semantic metadata.

### PI Configuration file

The `pi_config.json` file contains fields that **must** be configured prior to importing the XML file into a PI Server instance. Please indicate the **server** name and the **database** name. Please input the name or IP address of the machine running the server instance for **server**. For **database**, enter either the name of an existing database that you wish to update, or a new name to create a new one.
Please refer to `docs\CONFIGURING-PI-manual.md` for additional information on the configuration file.

#### AFXML reference

Asset Framework XML (AFXML) is the XML schema used in the PI software suite for storing and exchanging data across systems. It is proprietary, and is typically included with the installation files of PI Asset Framework. We have partially represented it in Python, along with a simple API for creating and modifying XML files that respect the AFXML schema. This method is directly inspired by the solution used in the [bsyncpy project](https://github.com/BuildingSync/bsyncpy).
We recommend against modifying `afxml.py` without reading `docs\AFXML-manual.md` first. 

#### TTL_to_AF library

This file is the core library that converts a BRICK model into a hierarchical structure compatible with PI Server. It reads a Turtle (`.ttl`) file and parses a BRICK model, assigns it a hierarchy compatible with an XML tree, translates relationships and other graph information into attributes and finally exports a new model into an XML file that can be loaded into a PI Server database. An extensive explanation on how the models are assembled is given in `docs\TTL_TO_AF-manual.md`

#### Utilities library

The `utilities.py` file contains utilities for configuring SPARQL queries and SHACL shapes.