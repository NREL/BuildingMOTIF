import re
from abc import ABC, abstractmethod
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

    def __eq__(self, other):
        """
        Compare two token results on every
        field except for the error field.
        """
        if not isinstance(other, TokenResult):
            return False
        return (
            self.value == other.value
            and self.token == other.token
            and self.length == other.length
        )


# null token result
ErrorTokenResult = TokenResult(None, Null(), 0, None)


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
class Parser(ABC):
    @abstractmethod
    def __call__(self, *args) -> List[TokenResult]:
        pass


class string(Parser):
    """Constructs a parser that matches a string."""

    def __init__(self, s: str, type_name: TokenOrConstructor):
        self.s = s
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        if target.startswith(self.s):
            return [
                TokenResult(self.s, ensure_token(self.type_name, self.s), len(self.s))
            ]
        return [
            TokenResult(
                None, Null(), 0, f"Expected {self.s}, got {target[:len(self.s)]}"
            )
        ]


class rest(Parser):
    """Constructs a parser that matches the rest of the string."""

    def __init__(self, type_name: TokenOrConstructor):
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        return [TokenResult(target, ensure_token(self.type_name, target), len(target))]


class substring_n(Parser):
    """Constructs a parser that matches a substring of length n."""

    def __init__(self, length, type_name: TokenOrConstructor):
        self.length = length
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        if len(target) >= self.length:
            value = target[: self.length]
            return [
                TokenResult(value, ensure_token(self.type_name, value), self.length)
            ]
        return [
            TokenResult(
                None,
                Null(),
                0,
                f"Expected {self.length} characters, got {target[:self.length]}",
            )
        ]


class regex(Parser):
    """Constructs a parser that matches a regular expression."""

    def __init__(self, r, type_name: TokenOrConstructor):
        self.r = r
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        match = re.match(self.r, target)
        if match:
            value = match.group()
            return [TokenResult(value, ensure_token(self.type_name, value), len(value))]
        return [
            TokenResult(
                None, Null(), 0, f"Expected {self.r}, got {target[:len(self.r)]}"
            )
        ]


class choice(Parser):
    """Constructs a choice combinator of parsers."""

    def __init__(self, *parsers):
        self.parsers = parsers

    def __call__(self, target: str) -> List[TokenResult]:
        errors = []
        for p in self.parsers:
            result = p(target)
            if result and not any(r.error for r in result):
                return result
            if result:
                errors.append(result[0].error)
        return [TokenResult(None, Null(), 0, " | ".join(errors))]


class constant(Parser):
    """Matches a constant token."""

    def __init__(self, type_name: Token):
        self.type_name = type_name

    def __call__(self, target: str) -> List[TokenResult]:
        return [TokenResult(None, self.type_name, 0)]


class abbreviations(Parser):
    """Constructs a choice combinator of string matching based on a dictionary."""

    def __init__(self, patterns):
        patterns = patterns
        parsers = [string(s, Constant(t)) for s, t in patterns.items()]
        self.choice = choice(*parsers)

    def __call__(self, target):
        return self.choice(target)


class sequence(Parser):
    """Applies parsers in sequence. All parsers must match consecutively."""

    def __init__(self, *parsers):
        self.parsers = parsers

    def __call__(self, target: str) -> List[TokenResult]:
        results = []
        total_length = 0
        for p in self.parsers:
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


class many(Parser):
    """Applies the given sequence parser repeatedly until it stops matching."""

    def __init__(self, seq_parser):
        self.seq_parser = seq_parser

    def __call__(self, target):
        results = []
        while True:
            part = self.seq_parser(target)
            if not part or part[0].value is None:
                break
            results.extend(part)
            # add up the length of all the tokens
            total_length = sum([r.length for r in part])
            target = target[total_length:]
        return results


class maybe(Parser):
    """Applies the given parser, but does not fail if it does not match."""

    def __init__(self, parser: Parser):
        self.parser = parser

    def __call__(self, target):
        result = self.parser(target)
        # if the result is not empty and there are no errors, return the result, otherwise return a null token
        if result and not any(r.error for r in result):
            return result
        return [TokenResult(None, Null(), 0)]


class until(Parser):
    """
    Constructs a parser that matches everything until the given parser matches.
    STarts with a string length of 1 and increments it until the parser matches.
    """

    def __init__(self, parser, type_name: TokenOrConstructor):
        self.parser = parser
        self.type_name = type_name

    def __call__(self, target):
        length = 1
        while length <= len(target):
            result = self.parser(target[length:])
            if result and not any(r.error for r in result):
                return [
                    TokenResult(
                        target[:length],
                        ensure_token(self.type_name, target[:length]),
                        length,
                    )
                ]
            length += 1
        return [
            TokenResult(
                None, Null(), 0, f"Expected {self.type_name}, got {target[:length]}"
            )
        ]


class extend_if_match(Parser):
    """Adds the type to the token result."""

    def __init__(self, parser, type_name: Token):
        self.parser = parser
        self.type_name = type_name

    def __call__(self, target):
        result = self.parser(target)
        if result and not any(r.error for r in result):
            result.extend([TokenResult(None, self.type_name, 0)])
            return result
        return result


def as_identifier(parser):
    """
    If the parser matches, add a new Identifier token after
    every Constant token in the result. The Identifier token
    has the same string value as the Constant token.
    """

    def as_identifier_parser(target):
        result = parser(target)
        if result and not any(r.error for r in result):
            new_result = []
            for r in result:
                new_result.append(r)
                if isinstance(r.token, Constant):
                    # length of the new token must be given as 0 so that the substring
                    # is not double counted
                    new_result.append(TokenResult(r.value, Identifier(r.value), 0))
            return new_result
        return result

    return as_identifier_parser


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
        first = None
        while True:
            try:
                # get first constant or identifier token using itertools
                first = first_true(
                    parts, pred=lambda x: isinstance(x.token, (Constant, Identifier))
                )
                # get the next constant or identifier token
                second = first_true(
                    parts, pred=lambda x: isinstance(x.token, (Constant, Identifier))
                )
                if not first or not second:
                    break
                # add the constant and identifier to the token dictionary
                identifier = first if isinstance(first.token, Identifier) else second
                constant = first if isinstance(first.token, Constant) else second
                res["tokens"].append(
                    {
                        "identifier": identifier.token.value,
                        "type": constant.token.value.toPython(),
                    }
                )
            except StopIteration:
                break
        if first is None:
            # if there are any constants left, add them to the token dictionary with the label
            first = first_true(parts, pred=lambda x: isinstance(x.token, Constant))
        if first:
            res["tokens"].append(
                {"identifier": r, "type": first.token.value.toPython()}
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
