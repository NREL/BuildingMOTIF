import uuid

from rdflib import Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.dataclasses import Model, ShapeCollection, ValidationContext
from buildingmotif.namespaces import RDF


def test_create_validation_context(clean_building_motif, monkeypatch):
    # Set up
    model = Model.create(name="https://example.com", description="a very good model")
    report = Graph()
    report.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))
    shape_collection1 = ShapeCollection.create()
    shape_collection2 = ShapeCollection.create()

    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    # Action
    validation_context = ValidationContext.create(
        shape_collections=[shape_collection1, shape_collection2],
        valid=False,
        report_string="blah blah blah",
        report=report,
        model=model,
    )

    # Assert
    assert validation_context.id == 1
    assert not validation_context.valid
    assert validation_context.report_string == "blah blah blah"
    assert isomorphic(validation_context.get_report(), report)
    assert validation_context.get_shape_collections() == [
        shape_collection1,
        shape_collection2,
    ]
    assert validation_context.get_model() == model

    db_validation_context = (
        clean_building_motif.table_connection.get_db_validation_context(
            validation_context.id
        )
    )
    assert db_validation_context.id == 1
    assert not db_validation_context.valid
    assert db_validation_context.report_string == "blah blah blah"
    assert db_validation_context.report_id == str(mocked_uuid)
    assert {sc.id for sc in db_validation_context.shape_collections} == {
        shape_collection1.id,
        shape_collection2.id,
    }
    assert db_validation_context.model_id == model.id
    stored_report = report
    assert isomorphic(stored_report, report)


def test_get_validation_contexts(clean_building_motif):
    # Set up
    model = Model.create(name="https://example.com", description="a very good model")
    report = Graph()
    report.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))
    shape_collection1 = ShapeCollection.create()
    shape_collection2 = ShapeCollection.create()

    validation_context = ValidationContext.create(
        shape_collections=[shape_collection1, shape_collection2],
        valid=False,
        report_string="blah blah blah",
        report=report,
        model=model,
    )

    # Action
    loaded_validation_context = ValidationContext.load(validation_context.id)

    # Assert
    assert (
        loaded_validation_context.get_shape_collections()
        == validation_context.get_shape_collections()
    )
    assert loaded_validation_context.valid == validation_context.valid
    assert loaded_validation_context.report_string == validation_context.report_string
    assert isomorphic(
        loaded_validation_context.get_report(), validation_context.get_report()
    )
    assert loaded_validation_context.get_model() == validation_context.get_model()
