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
import os

from buildingmotif.building_motif import BuildingMotif
```

```python
file = "./test.db"
os.remove(file) 

building_motif = BuildingMotif(f"sqlite:///{file}")
building_motif.session

```

```python
tl = building_motif.table_con.create_db_template_library("my_tl")
tl
```

```python
t = building_motif.table_con.create_db_template(
    name="my_t",
    head=["name", "zone"],
    template_library_id=tl.id
)

print(t)
print(t.head)
```

```python
try:
    t.head = ["nope"]
except AttributeError:
    pass

# this unforunately passes, but doesn't change the template
t.head.append("nope")
assert "nope" not in t.head
```

```python

```

```python

```
