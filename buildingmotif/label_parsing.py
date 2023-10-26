import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Union

from rdflib import URIRef

from buildingmotif.namespaces import BRICK

# TODO: programming by example?
# TODO: get LLM to write a parser for the point labels, given a human description

# Token is a union of the different types of tokens
Token = Union["Identifier", "Constant", "Delimiter", "Null"]
TokenOrConstructor = Union[Token, type]


def ensure_token(token_or_constructor: TokenOrConstructor, value):
    """Ensure a value is a token or constructs one from a given value."""
    if isinstance(token_or_constructor, type):
        return token_or_constructor(value)
    return token_or_constructor


@dataclass(frozen=True)
class Identifier:
    """An identifier token. Contains a string."""

    value: str


@dataclass(frozen=True)
class Constant:
    """A constant token. Contains a URI, probably some sort of Class"""

    value: URIRef


@dataclass(frozen=True)
class Delimiter:
    """A delimiter token."""

    value: str


@dataclass(frozen=True)
class Null:
    """A null token."""

    value: None = None


@dataclass(frozen=True)
class TokenResult:
    """A token result. Contains a token, the type of the token, the length of the token, and a possible error."""

    value: Optional[str]
    token: Token
    length: int
    error: Optional[str] = None


# type definition for the output of a parser function
@dataclass(frozen=True)
class ParseResult:
    tokens: List[TokenResult]
    success: bool
    _errors: List[str] = field(default_factory=list)

    @property
    def errors(self):
        """Return a list of errors and the offset into the string
        where the error occurred."""
        errors = []
        offset = 0
        for t in self.tokens:
            if t.error:
                errors.append((t.error, offset))
            offset += t.length
        return errors


# type definition for the parser functions.
# A parser function takes a string and returns a list of tuples
# each tuple is a token, the type of the token, and the length of the token
# the length of the token is used to keep track of how much of the string
# has been parsed
Parser = Callable[[str], List[TokenResult]]


def string(s, type_name: TokenOrConstructor):
    """Constructs a parser that matches a string."""

    def parser(target: str) -> List[TokenResult]:
        if target.startswith(s):
            return [TokenResult(s, ensure_token(type_name, s), len(s))]
        return [TokenResult(None, Null(), 0, f"Expected {s}, got {target[:len(s)]}")]

    return parser


def substring_n(length, type_name: TokenOrConstructor):
    """Constructs a parser that matches a substring of length n."""

    def parser(target: str) -> List[TokenResult]:
        if len(target) >= length:
            value = target[:length]
            return [TokenResult(value, ensure_token(type_name, value), length)]
        return [
            TokenResult(
                None, Null(), 0, f"Expected {length} characters, got {target[:length]}"
            )
        ]

    return parser


def regex(r, type_name: TokenOrConstructor):
    """Constructs a parser that matches a regular expression."""

    def parser(target: str) -> List[TokenResult]:
        match = re.match(r, target)
        if match:
            value = match.group()
            return [TokenResult(value, ensure_token(type_name, value), len(value))]
        return [TokenResult(None, Null(), 0, f"Expected {r}, got {target[:len(r)]}")]

    return parser


def choice(*parsers):
    """Constructs a choice combinator of parsers."""

    def parser(target: str) -> List[TokenResult]:
        errors = []
        for p in parsers:
            result = p(target)
            if result and not any(r.error for r in result):
                return result
            if result:
                errors.append(result[0].error)
        return [TokenResult(None, Null(), 0, " | ".join(errors))]

    return parser


def constant(type_name: Token):
    """Matches a constant token."""

    def parser(target: str) -> List[TokenResult]:
        return [TokenResult(None, type_name, 0)]

    return parser


def abbreviations(patterns):
    """Constructs a choice combinator of string matching based on a dictionary."""
    parsers = [string(s, Constant(t)) for s, t in patterns.items()]
    return choice(*parsers)


def sequence(*parsers):
    """Applies parsers in sequence. All parsers must match consecutively."""

    def parser(target):
        results = []
        total_length = 0
        for p in parsers:
            result = p(target)
            if not result:
                raise Exception("Expected result")
            results.extend(result)
            # if there are any errors, return the results
            if any(r.error for r in result):
                return results
            # TODO: how to handle error?
            consumed_length = sum([r.length for r in result])
            target = target[consumed_length:]
            total_length += sum([r.length for r in result])
        return results

    return parser


def many(seq_parser):
    """Applies the given sequence parser repeatedly until it stops matching."""

    def parser(target):
        results = []
        while True:
            part = seq_parser(target)
            if not part:
                break
            results.extend(part)
            # add up the length of all the tokens
            total_length = sum([r.length for r in part])
            target = target[total_length:]
        return results

    return parser


def maybe(parser):
    """Applies the given parser, but does not fail if it does not match."""

    def maybe_parser(target):
        result = parser(target)
        # if the result is not empty and there are no errors, return the result, otherwise return a null token
        if result and not any(r.error for r in result):
            return result
        return [TokenResult(None, Null(), 0)]

    return maybe_parser


COMMON_EQUIP_ABBREVIATIONS_BRICK = {
    "AHU": BRICK.Air_Handling_Unit,
    "FCU": BRICK.Fan_Coil_Unit,
    "VAV": BRICK.Variable_Air_Volume_Box,
    "CRAC": BRICK.Computer_Room_Air_Conditioner,
    "HX": BRICK.Heat_Exchanger,
    "PMP": BRICK.Pump,
    "RVAV": BRICK.Variable_Air_Volume_Box_With_Reheat,
    "HP": BRICK.Heat_Pump,
    "RTU": BRICK.Rooftop_Unit,
    "DMP": BRICK.Damper,
    "STS": BRICK.Status,
    "VLV": BRICK.Valve,
    "CHVLV": BRICK.Chilled_Water_Valve,
    "HWVLV": BRICK.Hot_Water_Valve,
    "VFD": BRICK.Variable_Frequency_Drive,
    "CT": BRICK.Cooling_Tower,
    "MAU": BRICK.Makeup_Air_Unit,
    "R": BRICK.Room,
    "A": BRICK.Air_Handling_Unit,
}

COMMON_POINT_ABBREVIATIONS = {
    "ART": BRICK.Room_Temperature_Sensor,
    "TSP": BRICK.Air_Temperature_Setpoint,
    "HSP": BRICK.Air_Temperature_Heating_Setpoint,
    "CSP": BRICK.Air_Temperature_Cooling_Setpoint,
    "SP": BRICK.Setpoint,
    "CHWST": BRICK.Leaving_Chilled_Water_Temperature_Sensor,
    "CHWRT": BRICK.Entering_Chilled_Water_Temperature_Sensor,
    "HWST": BRICK.Leaving_Hot_Water_Temperature_Sensor,
    "HWRT": BRICK.Entering_Hot_Water_Temperature_Sensor,
    "CO": BRICK.CO_Sensor,
    "CO2": BRICK.CO2_Sensor,
    "T": BRICK.Temperature_Sensor,
    "FS": BRICK.Flow_Sensor,
    "PS": BRICK.Pressure_Sensor,
    "DPS": BRICK.Differential_Pressure_Sensor,
}

COMMON_ABBREVIATIONS = abbreviations(
    {**COMMON_EQUIP_ABBREVIATIONS_BRICK, **COMMON_POINT_ABBREVIATIONS}
)


# common parser combinators
equip_abbreviations = abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK)
point_abbreviations = abbreviations(COMMON_POINT_ABBREVIATIONS)
delimiters = regex(r"[._:/\- ]", Delimiter)
identifier = regex(r"[a-zA-Z0-9]+", Identifier)
named_equip = sequence(equip_abbreviations, maybe(delimiters), identifier)
named_point = sequence(point_abbreviations, maybe(delimiters), identifier)


# wrapper function for a parser that does the following:
# - apply the parser to the target
# - if the parser does not consume all the target, raise an error
# - return the result of the parser
def parse(parser: Parser, target: str) -> ParseResult:
    """
    Parse the given target string using the given parser.

    :param parser: the parsing combinator function
    :type parser: Parser
    :param target: the target string to parse
    :type target: str
    :return: the result of the parser
    :rtype: ParseResult
    """
    result = parser(target)
    # remove empty Null tokens from result
    result = [r for r in result if r.error or (not isinstance(r.token, Null))]
    # check length of target vs length of all results
    total_length = sum([r.length for r in result])
    return ParseResult(
        result, total_length == len(target), [r.error for r in result if r.error]
    )


# wrapper function for reading a list of strings
# applies a given parser to each string in the list
# returns a dictionary of the input strings to the result of the parser
# Keep track of all strings that fail to parse and return them in a list
def parse_list(
    parser, target_list
) -> Tuple[Dict[str, List[TokenResult]], Dict[str, List[TokenResult]]]:
    """
    Parse a list of strings using the given parser.

    :param parser: the parsing combinator function
    :type parser: Parser
    :param target_list: the list of strings to parse
    :type target_list: List[str]
    :return: a tuple of the results and failures
    """
    results = {}
    failed = {}
    for target in target_list:
        result = parse(parser, target)
        if result.success:
            results[target] = result.tokens
        else:
            failed[target] = result.tokens
    return results, failed


# from itertools documentation
def first_true(iterable, default=None, pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.

    """
    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pred, iterable), default)


# function which takes the results of parse_list and turns all of the
# results (not failures) into token dictionaries.
# A token dictionary has an 'identifier' key which is the label (the keys
# of the results dictionary), and then a list of tokens. A token is a dictionary
# with 'identifier' (the substring part of the result) and 'type' (the type of
# the result if it is a constant)
def results_to_tokens(results):
    tokens = []
    for r in results:
        res = {"label": r, "tokens": []}
        parts = iter(results[r])
        constant = None
        while True:
            try:
                # get first constant token using itertools
                constant = first_true(
                    parts, pred=lambda x: isinstance(x.token, Constant)
                )
                # get the next identifier token
                identifier = first_true(
                    parts, pred=lambda x: isinstance(x.token, Identifier)
                )
                if not constant or not identifier:
                    break
                # add the constant and identifier to the token dictionary
                res["tokens"].append(
                    {
                        "identifier": identifier.token.value,
                        "type": constant.token.value.toPython(),
                    }
                )
            except StopIteration:
                break
        if constant is None:
            # if there are any constants left, add them to the token dictionary with the label
            constant = first_true(parts, pred=lambda x: isinstance(x.token, Constant))
        if constant:
            res["tokens"].append(
                {"identifier": r, "type": constant.token.value.toPython()}
            )
        tokens.append(res)

    return tokens


# Analyzes the failures of a parser to capture all point labels.
# For each label in the failures, compute the length of the found tokens.
# Create a dictionary keyed with the label. The value should have two keys.
# The first key is the remaining "unparsed" part of the string, the second key
# is the set of tokens that were found.
def analyze_failures(failures: Dict[str, List[TokenResult]]):
    """Analyze the failures of a parser."""
    analyzed = {}
    for failure in failures:
        tokens = failures[failure]
        length = sum([t.length for t in tokens])
        analyzed[failure] = {
            "unparsed": failure[length:],
            "tokens": [
                {"identifier": t.token.value, "type": t.token.value} for t in tokens
            ],
        }
    # group the points by the unparsed portion
    grouped = defaultdict(list)
    for f in analyzed:
        grouped[analyzed[f]["unparsed"]].append(f)
    # for each group, add the tokens to the first point in the group
    return grouped
