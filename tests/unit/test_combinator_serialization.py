from buildingmotif.api.serializers.parser import deserialize, serialize
from buildingmotif.label_parsing.combinators import (
    COMMON_ABBREVIATIONS,
    COMMON_EQUIP_ABBREVIATIONS_BRICK,
    abbreviations,
    choice,
    constant,
    many,
    maybe,
    regex,
    sequence,
    string,
    substring_n,
)
from buildingmotif.label_parsing.tokens import (
    Constant,
    Delimiter,
    ErrorTokenResult,
    Identifier,
    Null,
    TokenResult,
)
from buildingmotif.namespaces import BRICK


def test_string_parser():
    parser = deserialize(serialize(string("abc", Identifier)))
    # Test that it parses the exact string
    assert parser("abc") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it pulls the substring and leaves the rest
    assert parser("abcd") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it does not parse the string if it is not at the beginning
    assert parser("0abc") == [
        ErrorTokenResult
    ], f"Should not parse the string {parser('0abc')}"


def test_substring_n_parser():
    parser = deserialize(serialize(substring_n(2, Identifier)))
    # test that it pulls the correct number of characters when there are more than it needs
    assert parser("abc") == [
        TokenResult("ab", Identifier("ab"), 2)
    ], "Should parse the string"
    # test that it pulls the correct number of characters when there are less than it needs
    assert parser("a") == [ErrorTokenResult], "Should not parse the string"
    # test that it pulls the correct number of characters when there are exactly the number it needs
    assert parser("ab") == [
        TokenResult("ab", Identifier("ab"), 2)
    ], "Should parse the string"


def test_regex_parser():
    parser = deserialize(serialize(regex(r"[/\-:_]+", Delimiter)))
    # test pulling just 1 character
    assert parser("-abc") == [
        TokenResult("-", Delimiter("-"), 1)
    ], "Should parse the string"
    # test pulling multiple characters
    assert parser("::_abc") == [
        TokenResult("::_", Delimiter("::_"), 3)
    ], "Should parse the string"


def test_choice_parser():
    parser = deserialize(
        serialize(choice(string("abc", Identifier), string("def", Identifier)))
    )
    # test that it parses the first string
    assert parser("abc") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it parses the second string
    assert parser("def") == [
        TokenResult("def", Identifier("def"), 3)
    ], "Should parse the string"

    # test parsing order
    parser = deserialize(
        serialize(choice(string("abc", Identifier), string("ab", Identifier)))
    )
    # test that it parses the first string
    assert parser("abc") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it parses the second string
    assert parser("ab") == [
        TokenResult("ab", Identifier("ab"), 2)
    ], "Should parse the string"

    # more complex parser
    parser = deserialize(
        serialize(
            choice(
                string("abc", Identifier),
                string("def", Identifier),
                regex(r"[/\-:_]+", Delimiter),
            )
        )
    )
    # test that it parses the first string
    assert parser("abc") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it parses the second string
    assert parser("def") == [
        TokenResult("def", Identifier("def"), 3)
    ], "Should parse the string"
    # test the regex matches
    assert parser("-abc") == [
        TokenResult("-", Delimiter("-"), 1)
    ], "Should parse the string"
    assert parser("doesnotmatch") == [
        TokenResult(None, Null(), 0)
    ], "Should not parse the string"
    assert parser("abdef") == [
        TokenResult(None, Null(), 0)
    ], "Should not parse the string"


def test_constant_parser():
    parser = deserialize(serialize(constant(Constant(BRICK.Air_Handling_Unit))))
    # test that the constant is emitted
    assert parser("abc") == [
        TokenResult(None, Constant(BRICK.Air_Handling_Unit), 0)
    ], "Should parse the string"
    assert parser("") == [
        TokenResult(None, Constant(BRICK.Air_Handling_Unit), 0)
    ], "Should parse the string"


def test_abbreviations():
    parser = deserialize(serialize(abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK)))
    # test that the constant is emitted
    assert parser("AHU") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3)
    ], "Should parse the string"
    # test that only the matching characters are consumed
    assert parser("AHU1") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3)
    ], "Should parse the string"
    assert parser("BADABBREVIATION") == [
        TokenResult(None, Null(), 0)
    ], "Should not parse the string"


def test_sequence():
    parser = deserialize(
        serialize(sequence(string("abc", Identifier), string("def", Identifier)))
    )
    # test that it parses the whole sequence
    assert parser("abcdef") == [
        TokenResult("abc", Identifier("abc"), 3),
        TokenResult("def", Identifier("def"), 3),
    ], "Should parse the string"

    # test multiple kinds of parsers inside
    parser = deserialize(
        serialize(
            sequence(
                abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK),
                regex(r"[/\-:_]+", Delimiter),
                regex(r"[0-9]+", Identifier),
            )
        )
    )

    # test that only the matching characters are consumed
    assert parser("AHU-1") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        TokenResult("-", Delimiter("-"), 1),
        TokenResult("1", Identifier("1"), 1),
    ], "Should parse the string"
    assert parser("AHU1-") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        ErrorTokenResult,
    ], "Should not parse all of the string"


def test_many():
    delim = regex(r"[_\-:/]+", Delimiter)
    type_ident_delim = deserialize(
        serialize(
            sequence(
                COMMON_ABBREVIATIONS,
                regex(r"\d+", Identifier),
                delim,
            )
        )
    )
    parser = many(type_ident_delim)

    # test that it parses the whole sequence
    assert parser("AHU1") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        TokenResult("1", Identifier("1"), 1),
        ErrorTokenResult,
    ]
    # no delimiter at the end, so it should not parse the whole thing
    assert parser("AHU1/SP2") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        TokenResult("1", Identifier("1"), 1),
        TokenResult("/", Delimiter("/"), 1),
        TokenResult("SP", Constant(BRICK.Setpoint), 2),
        TokenResult("2", Identifier("2"), 1),
        ErrorTokenResult,
    ]
    # test that it parses multiple sequences
    assert parser("AHU1/SP2/") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        TokenResult("1", Identifier("1"), 1),
        TokenResult("/", Delimiter("/"), 1),
        TokenResult("SP", Constant(BRICK.Setpoint), 2),
        TokenResult("2", Identifier("2"), 1),
        TokenResult("/", Delimiter("/"), 1),
    ]


def test_maybe():
    parser = deserialize(
        serialize(sequence(maybe(string("abc", Identifier)), string("def", Identifier)))
    )
    # test that it parses the whole sequence
    assert parser("abcdef") == [
        TokenResult("abc", Identifier("abc"), 3),
        TokenResult("def", Identifier("def"), 3),
    ], "Should parse the string"
    assert parser("def") == [
        TokenResult(None, Null(), 0),
        TokenResult("def", Identifier("def"), 3),
    ], "Should parse the string"

    # test sequence inside maybe
    parser = deserialize(
        serialize(
            sequence(
                maybe(
                    sequence(
                        string("abc", Identifier),
                        string("def", Identifier),
                    )
                ),
                string("ghi", Identifier),
            )
        )
    )
    assert parser("ghi") == [
        TokenResult(None, Null(), 0),
        TokenResult("ghi", Identifier("ghi"), 3),
    ], "Should parse the string"

    assert parser("abcdefghi") == [
        TokenResult("abc", Identifier("abc"), 3),
        TokenResult("def", Identifier("def"), 3),
        TokenResult("ghi", Identifier("ghi"), 3),
    ], "Should parse the string"

    # test maybe inside sequence
    parser = deserialize(
        serialize(
            sequence(
                string("abc", Identifier),
                maybe(
                    sequence(
                        string("def", Identifier),
                        string("ghi", Identifier),
                    )
                ),
                string("jkl", Identifier),
            )
        )
    )
    assert parser("abcjkl") == [
        TokenResult("abc", Identifier("abc"), 3),
        TokenResult(None, Null(), 0),
        TokenResult("jkl", Identifier("jkl"), 3),
    ], "Should parse the string"

    assert parser("abcdefghijkl") == [
        TokenResult("abc", Identifier("abc"), 3),
        TokenResult("def", Identifier("def"), 3),
        TokenResult("ghi", Identifier("ghi"), 3),
        TokenResult("jkl", Identifier("jkl"), 3),
    ], "Should parse the string"
