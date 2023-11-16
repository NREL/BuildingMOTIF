import uuid

import pytest
from sqlalchemy.exc import NoResultFound


def test_create_db_validation_context(table_connection, monkeypatch):
    # Set up
    model = table_connection.create_db_model(
        name="my_db_model", description="a very good model"
    )

    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)

    # Action
    db_validation_context = table_connection.create_db_validation_context(
        valid=False, report_string="blah blah blah", model_id=model.id
    )

    # Assert
    assert db_validation_context.id == 1
    assert not db_validation_context.valid
    assert db_validation_context.report_string == "blah blah blah"
    assert db_validation_context.report_id == str(mocked_uuid)
    assert db_validation_context.shape_collections == []
    assert db_validation_context.model == model


def test_get_all_db_validation_contexts(table_connection, monkeypatch):
    # Set up
    model = table_connection.create_db_model(
        name="my_db_model", description="a very good model"
    )
    shape_collection1 = table_connection.create_db_shape_collection()
    shape_collection2 = table_connection.create_db_shape_collection()
    mocked_uuid = uuid.uuid4()

    def mockreturn():
        return mocked_uuid

    monkeypatch.setattr(uuid, "uuid4", mockreturn)
    db_validation_context = table_connection.create_db_validation_context(
        valid=False, report_string="blah blah blah", model_id=model.id
    )
    db_validation_context.shape_collections.append(shape_collection1)
    db_validation_context.shape_collections.append(shape_collection2)

    # Action
    result = table_connection.get_all_db_validation_contexts()

    # Assert
    assert len(result) == 1
    assert result[0].id == 1
    assert not result[0].valid
    assert result[0].report_string == "blah blah blah"
    assert result[0].report_id == str(mocked_uuid)
    assert result[0].shape_collections == [shape_collection1, shape_collection2]
    assert result[0].model == model


def test_get_db_validation_context(table_connection):
    # Set up
    model = table_connection.create_db_model(
        name="my_db_model", description="a very good model"
    )
    db_validation_context = table_connection.create_db_validation_context(
        valid=False, report_string="blah blah blah", model_id=model.id
    )

    # Action
    result = table_connection.get_db_validation_context(db_validation_context.id)

    # Assert
    assert result == db_validation_context


def test_get_db_validation_context_does_not_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.get_db_validation_context("I don't exist")


def test_delete_db_validation_context(table_connection):
    # Set
    model = table_connection.create_db_model(
        name="my_db_model", description="a very good model"
    )
    db_validation_context = table_connection.create_db_validation_context(
        valid=False, report_string="blah blah blah", model_id=model.id
    )

    # Action
    table_connection.delete_db_validation_context(db_validation_context.id)

    # Assert
    with pytest.raises(NoResultFound):
        table_connection.get_db_validation_context(db_validation_context.id)


def tests_delete_db_validation_context_does_does_exist(table_connection):
    with pytest.raises(NoResultFound):
        table_connection.delete_db_validation_context("does not exist")
