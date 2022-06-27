---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.13.8
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

```python
"""
This Notebook gives an intro on how to handle BuildingMotif's Sqlalachmely Session.
"""
import os

from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF
import sqlite3 as lite

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Template, Library, Model
from buildingmotif.database.tables import Base as BuildingMotif_tables_base
```

```python
"""
Create a testdb file, init a buiding_motif, and create a sqlite connection (for db transparency)
"""
file = "./test.db"
if os.path.isfile(file):
    os.remove(file) 

building_motif = BuildingMOTIF(f"sqlite:///{file}")
BuildingMotif_tables_base.metadata.create_all(building_motif.engine)
building_motif.session

conn = lite.connect(file)
cur = conn.cursor()

```

```python
"""
Create a Library. Note that while You can get
the library within the session, it is not writen
to the db until after the commit.
"""
lib = Library.create("my_library")
print(lib)
assert len(building_motif.table_connection.get_all_db_libraries()) == 1

cur.execute("SELECT * FROM library")
print(f"pre-commit library: {cur.fetchall()}")

building_motif.session.commit()

cur.execute("SELECT * FROM library")
print(f"post-commit library: {cur.fetchall()}")
```

```python
"""
Same thing with a template. 
"""
t = lib.create_template(name="my_template")
print(t)
assert lib.get_templates()[0] == t
assert len(building_motif.table_connection.get_all_db_templates()) == 1

cur.execute("SELECT * FROM template")
print(f"pre-commit template: {cur.fetchall()}")

building_motif.session.commit()

cur.execute("SELECT * FROM template")
print(f"post-commit template: {cur.fetchall()}")
```

```python
"""
Graphs abide by sessioning, too
"""
print(t.body)
t.body.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))
body_id = building_motif.table_connection.get_db_template_by_id(t.id).body_id
assert isomorphic(building_motif.graph_connection.get_graph(body_id), t.body)

cur.execute("SELECT * FROM kb_625d302a74_type_statements")
print(f"pre-commit statements: {cur.fetchall()}")

building_motif.session.commit()

cur.execute("SELECT * FROM kb_625d302a74_type_statements")
print(f"post-commit statements: {cur.fetchall()}")


```

```python
"""
You don't have to commit after each create. After each
create, we flush the session, so that the created object
is avaiable for reference.
"""
lib = Library.create("your_library")
t = lib.create_template(name="your_template")
t.body.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))

building_motif.session.commit()
```

```python
"""
A db error could happen on a flush or a commit, and you
will have to rollback to continue using the session.
"""
try:
    Library.create("my_library")
except Exception as e:
    print(f"{e}\n")
    building_motif.session.rollback()
    
bad_lib = Library.create("a fine name")
bad_lib.name = "my_library"
try:
    building_motif.session.commit()
except Exception as e:
    print(f"{e}\n")
    building_motif.session.rollback()
```

```python
"""
Remember buiding_motif.session is a unwrapped or modified 
Sqlalchemly Session, and using it comes with all the power
and complexity of sqlalchemly. Be sure to read the docs!

https://docs.sqlalchemy.org/en/14/orm/session_api.html
"""
```

```python

```
