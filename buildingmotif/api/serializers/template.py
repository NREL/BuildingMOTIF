from typing import List, Union

from typing_extensions import TypedDict

from buildingmotif.database.tables import DBTemplate

TemplateDict = TypedDict(
    "TemplateDict",
    {
        "id": int,
        "name": str,
        "body_id": str,
        "optional_args": List[str],
        "library_id": int,
        "dependency_ids": List[int],
    },
)


def serialize(
    param: Union[DBTemplate, List[DBTemplate]]
) -> Union[TemplateDict, List[TemplateDict]]:
    """serialize one or more templates

    :param param: one template or a list of templates
    :type param: Union[DBTemplate, List[DBTemplate]]
    :return: one json per serialized template
    :rtype: Union[TemplateDict, List[TemplateDict]]
    """
    if isinstance(param, DBTemplate):
        return _serialize(param)

    elif isinstance(param, list):
        return [_serialize(x) for x in param]

    raise ValueError("invalid input. Must be a DBTemplate or list of DBTemplates")


def _serialize(template: DBTemplate) -> TemplateDict:
    """serialize template

    :param template: template
    :type template: DBTemplate
    :return: serialized template
    :rtype: TemplateDict
    """
    return {
        "id": template.id,
        "name": template.name,
        "body_id": template.body_id,
        "optional_args": template.optional_args,
        "library_id": template.library_id,
        "dependency_ids": [d.id for d in template.dependencies],
    }
