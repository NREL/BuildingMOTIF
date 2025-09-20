import pytest

from buildingmotif.database.errors import (
    LibraryNotFound,
    ShapeCollectionNotFound,
    TemplateNotFound,
)
from buildingmotif.dataclasses.template import Template


def test_cascade_delete_model_shape_collection(bm):
    # Create a model; its manifest (shape collection) should be cascading deleted.
    db_model = bm.table_connection.create_db_model(
        name="cascade_model", description="test cascading delete on model"
    )
    shape_collection_id = db_model.manifest.id
    # assert we can get the shape collection
    assert bm.table_connection.get_db_shape_collection(shape_collection_id)
    # now delete the model, and assert the shape collection is gone
    bm.table_connection.delete_db_model(db_model.id)
    bm.session.commit()
    with pytest.raises(ShapeCollectionNotFound):
        bm.table_connection.get_db_shape_collection(shape_collection_id)


def test_cascade_delete_library_cascades(bm):
    # Create a library, two templates within it, and a dependency relationship.
    db_library = bm.table_connection.create_db_library(name="cascade_library")
    shape_collection_id = db_library.shape_collection.id
    template1 = bm.table_connection.create_db_template(
        name="template1", library_id=db_library.id
    )
    template2 = bm.table_connection.create_db_template(
        name="template2", library_id=db_library.id
    )

    # Add a dependency relationship between template1 and template2.
    template1 = Template.load(template1.id)
    template2 = Template.load(template2.id)
    template1.add_dependency(template2, {"name": "dependency"})
    # Verify the dependency exists.
    deps = bm.table_connection.get_db_template_dependencies(template1.id)
    assert len(deps) == 1

    # Deleting the library should cascade-delete the library, its templates, and its associated shape collection.
    bm.table_connection.delete_db_library(db_library.id)
    bm.session.commit()

    with pytest.raises(LibraryNotFound):
        bm.table_connection.get_db_library(db_library.id)
    with pytest.raises(TemplateNotFound):
        bm.table_connection.get_db_template(template1.id)
    with pytest.raises(TemplateNotFound):
        bm.table_connection.get_db_template(template2.id)
    with pytest.raises(ShapeCollectionNotFound):
        bm.table_connection.get_db_shape_collection(shape_collection_id)


# library1 has template1, library2 has template2, template1 depends on template2
# then deleting library1 should delete template1 but leave library2 and template2
def test_cascade_delete_dependent_multi_library(bm):
    # Create two libraries
    library1 = bm.table_connection.create_db_library(name="cascade_library1")
    library2 = bm.table_connection.create_db_library(name="cascade_library2")
    # Create template1 in library1 and template2 in library2
    template1 = bm.table_connection.create_db_template(
        name="template1", library_id=library1.id
    )
    template2 = bm.table_connection.create_db_template(
        name="template2", library_id=library2.id
    )
    # Load templates to add dependency and verify dependency relationship.
    template1 = Template.load(template1.id)
    template2 = Template.load(template2.id)
    # Add dependency: template1 depends on template2
    template1.add_dependency(template2, {"name": "dependency"})
    # Verify dependency exists.
    deps = bm.table_connection.get_db_template_dependencies(template1.id)
    assert len(deps) == 1
    # Delete library1 and ensure cascading deletion
    bm.table_connection.delete_db_library(library1.id)
    bm.session.commit()
    with pytest.raises(LibraryNotFound):
        bm.table_connection.get_db_library(library1.id)
    with pytest.raises(TemplateNotFound):
        bm.table_connection.get_db_template(template1.id)
    # Library2 and its template should still exist
    assert bm.table_connection.get_db_library(library2.id)
    assert bm.table_connection.get_db_template(template2.id)


# library1 has template1, library2 has template2, template1 depends on template2
# deleting library2 should delete template2 but leave library1 and template1
def test_cascade_delete_dependency_multi_library(bm):
    # Create two libraries
    library1 = bm.table_connection.create_db_library(name="cascade_library1")
    library2 = bm.table_connection.create_db_library(name="cascade_library2")
    # Create template1 in library1 and template2 in library2
    template1 = bm.table_connection.create_db_template(
        name="template1", library_id=library1.id
    )
    template2 = bm.table_connection.create_db_template(
        name="template2", library_id=library2.id
    )
    # Load templates to add dependency and verify dependency relationship.
    template1 = Template.load(template1.id)
    template2 = Template.load(template2.id)
    # Add dependency: template1 depends on template2
    template1.add_dependency(template2, {"name": "dependency"})
    # Verify dependency exists.
    deps = bm.table_connection.get_db_template_dependencies(template1.id)
    assert len(deps) == 1
    # Delete library2 and ensure cascading deletion
    bm.table_connection.delete_db_library(library2.id)
    bm.session.commit()
    with pytest.raises(LibraryNotFound):
        bm.table_connection.get_db_library(library2.id)
    with pytest.raises(TemplateNotFound):
        bm.table_connection.get_db_template(template2.id)

    # Library1 and its template should still be here
    bm.table_connection.get_db_library(library1.id)
    bm.table_connection.get_db_template(template1.id)


def test_depedency_resolves_after_library_replacement(bm):
    # Create two libraries
    library1 = bm.table_connection.create_db_library(name="cascade_library1")
    library2 = bm.table_connection.create_db_library(name="cascade_library2")
    # Create template1 in library1 and template2 in library2
    template1 = bm.table_connection.create_db_template(
        name="template1", library_id=library1.id
    )
    template2 = bm.table_connection.create_db_template(
        name="template2", library_id=library2.id
    )
    # Load templates to add dependency and verify dependency relationship.
    template1 = Template.load(template1.id)
    template2 = Template.load(template2.id)
    # Add dependency: template1 depends on template2
    template1.add_dependency(template2, {"name": "dependency"})
    # Verify dependency exists.
    deps = bm.table_connection.get_db_template_dependencies(template1.id)
    assert len(deps) == 1
    # Verify dependency resolves
    assert deps[0].dependency_template == bm.table_connection.get_db_template(
        template2.id
    )
    # Delete library2 and ensure cascading deletion
    bm.table_connection.delete_db_library(library2.id)
    bm.session.commit()
    with pytest.raises(LibraryNotFound):
        bm.table_connection.get_db_library(library2.id)
    with pytest.raises(TemplateNotFound):
        bm.table_connection.get_db_template(template2.id)
    # Verify dependency does not resolves
    assert deps[0].dependency_template is None
    library2 = bm.table_connection.create_db_library(name="cascade_library2")
    # Recreate template2 in library2
    template2 = bm.table_connection.create_db_template(
        name="template2", library_id=library2.id
    )
    # Verify dependency resolves
    assert deps[0].dependency_template == bm.table_connection.get_db_template(
        template2.id
    )
