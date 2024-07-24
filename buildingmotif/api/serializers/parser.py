import warnings
from functools import lru_cache
from inspect import Parameter, signature
from typing import Any, Type, Union, get_type_hints

from rdflib import URIRef
from typing_extensions import TypedDict

from buildingmotif.label_parsing import combinators  # noqa
from buildingmotif.label_parsing.parser import Parser
from buildingmotif.label_parsing.tokens import Token

ParserDict = TypedDict("ParserDict", {"parser": str, "args": dict})


def serialize(parser: Parser) -> ParserDict:
    """Serialize a parser into a TypedDict.

    :param parser: a parser
    :type parser: Parser
    :return: a dict ready for JSON serialization
    :rtype: ParserDict
    """
    parser_dict: ParserDict = {
        "parser": parser.__class__.__name__,
        "args": _serialize(parser.__args__),  # type: ignore
    }

    return parser_dict


def _serialize(collection: Union[dict, list, tuple]) -> Union[dict, list]:
    """Serialize a collection and the contents of that collection into a dict or list

    :param collection: collection to serialize
    :type collection: Union[dict, list, tuple]
    :return: serialized collection
    :rtype: Union[dict, list]
    """

    def _serialize_item(item):
        if isinstance(item, URIRef):
            return str(item)
        elif isinstance(item, str) or isinstance(item, int) or isinstance(item, float):
            return item
        elif item in [None, True, False]:
            return item
        elif isinstance(item, Parser):
            return serialize(item)
        if isinstance(item, type) and issubclass(item, Token):
            return {"token": item.__name__}
        if isinstance(item, Token):
            return {"token": item.__class__.__name__, "value": str(item.value)}
        if isinstance(item, list) or isinstance(item, dict) or isinstance(item, tuple):
            return _serialize(item)
        warnings.warn(
            f"Serialization does not exist for object of class {item.__class__} this may cause JSON serialization to fail"
        )
        return item

    serialized_collection: Union[dict, list]
    if isinstance(collection, dict):
        serialized_collection = {}
        for key, item in collection.items():
            serialized_collection[key] = _serialize_item(item)
    else:
        serialized_collection = list(map(_serialize_item, collection))
    return serialized_collection


@lru_cache
def _get_parser_by_name(parser_name: str) -> Type[Parser]:
    """Get parser class by name of parser.

    :param parser_name: name of parser
    :type parser_name: str
    :return: parser class
    :rtype: Type[Parser]"""
    parsers = Parser.__subclasses__()
    for parser in parsers:
        if parser.__name__ == parser_name:
            return parser
    raise NameError(f'Parser of type "{parser_name}" does not exist')


@lru_cache
def _get_token_by_name(token_name: str) -> Type[Token]:
    """Get token class by name of token

    :param token_name: name of token
    :type token_name: str
    :return: token class
    :rtype: Type[Token]"""
    tokens = Token.__subclasses__()
    for token in tokens:
        if token.__name__ == token_name:
            return token
    raise NameError(f'Token of type "{token_name}" does not exist')


def _construct_class(cls: Type[Parser], args_dict: dict) -> Parser:
    """Construct class from type and arguments

    :param cls: type of class to construct
    :type cls: Type
    :param args: arguments
    :type args: dict
    :return: Instance of class
    :rtype: Any"""
    parameters = signature(cls.__init__).parameters
    args = []
    kwargs = {}
    for name, param in parameters.items():
        if name not in args_dict:
            continue
        kind = param.kind
        value = args_dict[name]
        if kind == Parameter.POSITIONAL_ONLY:
            args.append(value)
        elif kind in [Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY]:
            kwargs[name] = value
        elif kind == Parameter.VAR_POSITIONAL:
            args = [*args, *value]
        elif kind == Parameter.VAR_KEYWORD:
            kwargs.update(value)

    return cls(*args, **kwargs)


def deserialize(parser_dict: Union[ParserDict, dict]) -> Parser:
    """Deserialize a parser from a TypedDict.

    :param parser_dict: dict containing serialized parser
    :type parser_dict: ParserDict
    :return: deserialized parser
    :rtype: Parser
    """
    if not _parser_like(parser_dict):
        raise TypeError("parser_dict is incorrectly formed")
    args_dict = dict(
        (arg, _deserialize(item)) for arg, item in parser_dict["args"].items()
    )
    parser = _get_parser_by_name(parser_dict["parser"])
    return _construct_class(parser, args_dict)


@lru_cache
def _get_token_value_type(token: Type[Token]) -> Type:
    """Get the type of the token's value argument.

    :param token: token to inspect
    :type token: Token
    :return: type of value argument
    :rtype: Type"""
    return get_type_hints(token.__init__)["value"]


def _deserialize_token(token_dict: dict) -> Union[Token, Type[Token]]:
    """Deserialize token dict

    :param token_dict: dict containing token
    :type token_dict: dict
    :return: deserialized token
    :rtype: Token"""
    token = _get_token_by_name(token_dict["token"])
    if "value" in token_dict:
        value_type = _get_token_value_type(token)  # type: ignore
        return token(value_type(token_dict["value"]))
    return token


def _deserialize(item: Any) -> Any:
    """Deserialize an item

    :param item: item to deserialize
    :type item: Any
    :return: deserialized item
    :rtype: Any
    """
    if isinstance(item, str) or isinstance(item, int) or isinstance(item, float):
        return item
    elif item in [None, True, False]:
        return item
    elif isinstance(item, dict):
        if _parser_like(item):
            return deserialize(item)
        elif _token_like(item):
            return _deserialize_token(item)
        else:
            return dict((key, _deserialize(value)) for key, value in item.items())
    elif isinstance(item, list):
        return list(map(_deserialize, item))
    warnings.warn(
        f"Serialized object contained unexpected type: {item.__class__.__name__}"
    )
    return item


def _parser_like(item: Union[dict, ParserDict]) -> bool:
    """Does a dict look like a serialized parser

    :param item: dict to inspect
    :type item: dict
    :return: does the dict look like a serialized parser
    :rtype: bool
    """
    if len(item) != 2:
        return False
    if "args" not in item:
        return False
    if "parser" not in item:
        return False
    return True


def _token_like(item: dict) -> bool:
    """Does the dict look like a serialized token

    :param item: dict to inspect
    :type item: dict
    :return: does the dict look like a serialized token
    :rtype: bool
    """
    if len(item) > 2:
        return False
    if "token" not in item:
        return False
    return True
