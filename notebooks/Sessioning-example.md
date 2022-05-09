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
This Notebook gives an intro on how to handle BuildingMotifs Sqlalachmely Session.
"""
import os

from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF
import sqlite3 as lite

from buildingmotif.building_motif import BuildingMotif
from buildingmotif.dataclasses.template import Template
from buildingmotif.dataclasses.template_library import TemplateLibrary
from buildingmotif.dataclasses.model import Model

```

```python
"""
Create a testdb file, init a buiding_motif, and create a sqlite connection (for db transparency)
"""
file = "./test.db"
os.remove(file) 

building_motif = BuildingMotif(f"sqlite:///{file}")
building_motif.session

conn = lite.connect(file)
cur = conn.cursor()

```

```python
"""
Create a Template Library. Note that while You can get
the template library within the session, it is not writen
to the db until after the commit.
"""
tl = TemplateLibrary.create("my_template_library")
print(tl)
assert len(building_motif.table_con.get_all_db_template_libraries()) == 1

cur.execute("SELECT * FROM template_library")
print(f"pre-commit template_library: {cur.fetchall()}")

building_motif.session.commit()

cur.execute("SELECT * FROM template_library")
print(f"post-commit template_library: {cur.fetchall()}")
```

```python
"""
Same thing with a template. 
"""
t = tl.create_template(name="my_template")
print(t)
assert tl.get_templates()[0] == t
assert len(building_motif.table_con.get_all_db_templates()) == 1

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
body_id = building_motif.table_con.get_db_template(t.id).body_id
assert isomorphic(building_motif.graph_con.get_graph(body_id), t.body)

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
tl = TemplateLibrary.create("your_template_library")
t = tl.create_template(name="your_template")
t.body.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))

building_motif.session.commit()
```

```python
"""
A db error could happen on a flush or a commit, and you
will have to rollback to continue using the session.
"""
try:
    TemplateLibrary.create("my_template_library")
except Exception as e:
    print(f"{e}\n")
    building_motif.session.rollback()
    
bad_tl = TemplateLibrary.create("a fine name")
bad_tl.name = "my_template_library"
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
