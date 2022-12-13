from typing import List, Union

from typing_extensions import NotRequired, TypedDict

from buildingmotif.database.tables import DBTemplate
from buildingmotif.dataclasses.template import Template

TemplateDict = TypedDict(
    "TemplateDict",
    {
        "id": int,
        "name": str,
        "body_id": str,
        "optional_args": List[str],
        "library_id": int,
        "dependency_ids": List[int],
        "parameters": NotRequired[List[str]],
    },
)


def serialize(
    param: Union[DBTemplate, List[DBTemplate]], include_parameters: bool = False
) -> Union[TemplateDict, List[TemplateDict]]:
    """Serialize one or more templates into a TypedDict.

    :param param: one template or a list of templates.
    :type param: Union[DBTemplate, List[DBTemplate]]
    :param include_parameters: to include parameters, default False
    :type include_parameters: bool
    :raises ValueError: if invalid input
    :return: one JSON per serialized template
    :rtype: Union[TemplateDict, List[TemplateDict]]
    """
    if isinstance(param, DBTemplate):
        return _serialize(param, include_parameters)

    elif isinstance(param, list):
        return [_serialize(x, include_parameters) for x in param]

    raise ValueError("invalid input. Must be a DBTemplate or list of DBTemplates")


def _serialize(template: DBTemplate) -> TemplateDict:
    """Serialize a template into a TypedDict.

    :param template: template
    :type template: DBTemplate
    :param include_parameters: to include parameters, default False
    :type include_parameters: bool
    :return: serialized template
    :rtype: TemplateDict
    """
    res: TemplateDict = {
        "id": template.id,
        "name": template.name,
        "body_id": template.body_id,
        "optional_args": template.optional_args,
        "library_id": template.library_id,
        "dependency_ids": [d.id for d in template.dependencies],
    }

    if include_parameters:
        parameters = Template.load(template.id).parameters
        res["parameters"] = sorted(
            list(parameters)
        )  # make it serzialiable and determintistic

    return res
