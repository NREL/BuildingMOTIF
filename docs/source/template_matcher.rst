Template Matching
=============

Overview
========

*Template matching* is the process of identifying fully or partially evaluated templates inside a building graph, given the template definition.
We use the :class:`~buildingmotif.template_matcher.TemplateMatcher` class to perform template matching.
The matching is performed when the :class:`~buildingmotif.template_matcher.TemplateMatcher` class is instantiated; instantiation takes as arguments:

- the building graph (where you are searching for evaluated templates)
- the template definition (the template you are looking for)
- an ontology graph to help match nodes semantically

.. code-block:: python
   
    # for loading templates from a file
    from building_motif.template import TemplateLibrary
    # for performing the template matching
    from buildingmotif.template_matcher import TemplateMatcher
    from buildingmotif.utils import new_temporary_graph

    # load the building graph
    building = new_temporary_graph()
    building.parse("my_building.ttl")

    # load the ontology
    ontology = new_temporary_graph()
    ontology.parse("Brick.ttl")

    # load the templates from a file
    templates = TemplateLibrary("my_templates/")
    # get the template you want to match
    vav_template = templates["vav-template"][0]

    # run the template matching process
    matcher = TemplateMatcher(building, vav_template, ontology)

It may take a few seconds to perform the matching, depending on the size of the building graph and template. Larger graphs may take exponentially longer to search for template matches.

After the matching is complete, the resulting `TemplateMatcher` object can be used to fetch:

- the *mappings* for each match: a mapping is a dictionary relating a node in the building graph to a node in the template
- the *building subgraph* for each match: this is the part of the building graph that was matched to the template
- the *partial template* for each match: this is what nodes and edges were *not found* in the building graph


.. code-block:: python

   size = matcher.largest_mapping_size
   for mapping, subgraph in matcher.building_mapping_subgraphs_iter(size=size):
        print(mapping)
        print(subgraph.serialize(format="turtle"))
        leftover_template = matcher.remaining_template(mapping)
        print(f"Template now has params: {leftover_template.parameters}")

TemplateMatcher
------------
.. automodule:: buildingmotif.template_matcher
   :members:
   :undoc-members:
   :show-inheritance:
