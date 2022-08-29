from typing import List, Union

from typing_extensions import TypedDict

from buildingmotif.database.tables import DBLibrary

LibraryDict = TypedDict(
    "LibraryDict",
    {
        "id": int,
        "name": str,
        "template_ids": List[int],
        "shape_collection_id": int,
    },
)


def serialize(
    param: Union[DBLibrary, List[DBLibrary]]
) -> Union[LibraryDict, List[LibraryDict]]:
    """Serialize one or more library.

    :param param: one library or a list of libraries
    :type param: Union[DBLibrary, List[DBLibrary]]
    :return: one json per serialized library
    :rtype: Union[DBLibrary, List[DBLibrary]]
    """
    if isinstance(param, DBLibrary):
        return _serialize(param)

    elif isinstance(param, list):
        return [_serialize(x) for x in param]

    raise ValueError("invalid input. Must be a DBLibrary or list of DBLibraries")


def _serialize(library: DBLibrary) -> LibraryDict:
    """Serialize library.

    :param library: library
    :type library: DBTemplate
    :return: serialized library
    :rtype: LibraryDict
    """
    return {
        "id": library.id,
        "name": library.name,
        "template_ids": [t.id for t in library.templates],
        "shape_collection_id": library.shape_collection_id,
    }
