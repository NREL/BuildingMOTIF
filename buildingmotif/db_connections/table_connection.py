import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from buildingmotif.tables import Base, DBModel


class TableConnection:
    """Controls intercation with the db"""

    def __init__(self, db_uri: str) -> None:
        """create TableConnection

        :param db_uri: defaults to None
        :type db_uri: str, optional
        """
        # create engine
        engine = create_engine(db_uri, echo=True)

        # create tables
        Base.metadata.create_all(engine)

        # create session
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def create_db_model(self, name: str) -> DBModel:
        """create a DBModel

        :param name: name of dbmodel
        :type name: str
        :return: DBModel
        :rtype: DBModel
        """
        db_model = DBModel(name=name, graph_id=str(uuid.uuid4()))

        self.session.add(db_model)
        self.session.commit()

        return db_model

    def get_all_db_models(self) -> list("DBModel"):
        """get all db models

        :return: all DBModels
        :rtype: DBModel
        """
        return self.session.query(DBModel).all()

    def get_db_model(self, id: str) -> DBModel:
        """get DBModel from id

        :param id: id of DBModel
        :type id: str
        :return: DBModel
        :rtype: DBModel
        """
        return self.session.query(DBModel).filter(DBModel.id == id).one()

    def update_db_model_name(self, id: str, name: str) -> None:
        """update DBModel

        :param id: id of DBModel
        :type id: str
        :param name: new name
        :type name: str
        """
        db_model = self.session.query(DBModel).filter(DBModel.id == id).one()
        db_model.name = name

        self.session.commit()

    def delete_db_model(self, id: str) -> None:
        """delete DBModel

        :param id: id of deleted DBModel
        :type id: str
        """
        db_model = self.session.query(DBModel).filter(DBModel.id == id).one()

        self.session.delete(db_model)
        self.session.commit()
