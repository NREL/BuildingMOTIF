from typing import List, Union

from typing_extensions import TypedDict

from buildingmotif.database.tables import DBModel

ModelDict = TypedDict(
    "ModelDict",
    {
        "id": int,
        "name": str,
        "description": str,
        "graph_id": str,
    },
)


def serialize(
    param: Union[DBModel, List[DBModel]]
) -> Union[ModelDict, List[ModelDict]]:
    """Serialize one or more Models into a TypedDict.

    :param param: One Model or a List of Models.
    :type param: Union[DBModel, List[DBModel]]
    :return: One JSON per serialized Model.
    :rtype: Union[ModelDict, List[ModelDict]]
    """
    if isinstance(param, DBModel):
        return _serialize(param)

    elif isinstance(param, list):
        return [_serialize(x) for x in param]

    raise ValueError("invalid input. Must be a DBModel or list of DBModels")


def _serialize(model: DBModel) -> ModelDict:
    """Serialize a Model into a TypedDict.

    :param model: A Model.
    :type model: DBModel
    :return: A serialized Model.
    :rtype: ModelDict
    """
    return {
        "id": model.id,
        "name": model.name,
        "description": model.description,
        "graph_id": model.graph_id,
    }
