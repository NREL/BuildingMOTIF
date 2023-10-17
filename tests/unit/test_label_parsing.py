from buildingmotif.label_parsing import (
    COMMON_ABBREVIATIONS,
    COMMON_EQUIP_ABBREVIATIONS_BRICK,
    Constant,
    Delimiter,
    Identifier,
    TokenResult,
    abbreviations,
    choice,
    constant,
    ensure_token,
    first_true,
    many,
    parse,
    parse_list,
    regex,
    sequence,
    string,
    substring_n,
)
from buildingmotif.namespaces import BRICK


def test_ensure_token():
    assert ensure_token(Identifier, "abc") == Identifier(
        "abc"
    ), "Should instantiate the token if it is a type and not a value"
    assert ensure_token(Identifier("abc"), None) == Identifier(
        "abc"
    ), "Should return the token if it is a value"


def test_string_parser():
    parser = string("abc", Identifier)
    # Test that it parses the exact string
    assert parser("abc") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it pulls the substring and leaves the rest
    assert parser("abcd") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it does not parse the string if it is not at the beginning
    assert parser("0abc") == [], "Should not parse the string"


def test_substring_n_parser():
    parser = substring_n(2, Identifier)
    # test that it pulls the correct number of characters when there are more than it needs
    assert parser("abc") == [
        TokenResult("ab", Identifier("ab"), 2)
    ], "Should parse the string"
    # test that it pulls the correct number of characters when there are less than it needs
    assert parser("a") == [], "Should not parse the string"
    # test that it pulls the correct number of characters when there are exactly the number it needs
    assert parser("ab") == [
        TokenResult("ab", Identifier("ab"), 2)
    ], "Should parse the string"


def test_regex_parser():
    parser = regex(r"[/\-:_]+", Delimiter)
    # test pulling just 1 character
    assert parser("-abc") == [
        TokenResult("-", Delimiter("-"), 1)
    ], "Should parse the string"
    # test pulling multiple characters
    assert parser("::_abc") == [
        TokenResult("::_", Delimiter("::_"), 3)
    ], "Should parse the string"


def test_choice_parser():
    parser = choice(string("abc", Identifier), string("def", Identifier))
    # test that it parses the first string
    assert parser("abc") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it parses the second string
    assert parser("def") == [
        TokenResult("def", Identifier("def"), 3)
    ], "Should parse the string"

    # test parsing order
    parser = choice(string("abc", Identifier), string("ab", Identifier))
    # test that it parses the first string
    assert parser("abc") == [
        TokenResult("abc", Identifier("abc"), 3)
    ], "Should parse the string"
    # test that it parses the second string
    assert parser("ab") == [
        TokenResult("ab", Identifier("ab"), 2)
    ], "Should parse the string"

    # more complex parser
    parser = choice(
        string("abc", Identifier),
        string("def", Identifier),
        regex(r"[/\-:_]+", Delimiter),
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


def test_constant_parser():
    parser = constant(Constant(BRICK.Air_Handling_Unit))
    # test that the constant is emitted
    assert parser("abc") == [
        TokenResult(None, Constant(BRICK.Air_Handling_Unit), 0)
    ], "Should parse the string"
    assert parser("") == [
        TokenResult(None, Constant(BRICK.Air_Handling_Unit), 0)
    ], "Should parse the string"


def test_abbreviations():
    parser = abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK)
    # test that the constant is emitted
    assert parser("AHU") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3)
    ], "Should parse the string"
    # test that only the matching characters are consumed
    assert parser("AHU1") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3)
    ], "Should parse the string"


def test_sequence():
    parser = sequence(string("abc", Identifier), string("def", Identifier))
    # test that it parses the whole sequence
    assert parser("abcdef") == [
        TokenResult("abc", Identifier("abc"), 3),
        TokenResult("def", Identifier("def"), 3),
    ], "Should parse the string"

    # test multiple kinds of parsers inside
    parser = sequence(
        abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK),
        regex(r"[/\-:_]+", Delimiter),
        regex(r"[0-9]+", Identifier),
    )

    # test that only the matching characters are consumed
    assert parser("AHU-1") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        TokenResult("-", Delimiter("-"), 1),
        TokenResult("1", Identifier("1"), 1),
    ], "Should parse the string"
    assert parser("AHU1-") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3)
    ], "Should not parse all of the string"


def test_many():
    delim = regex(r"[_\-:/]+", Delimiter)
    type_ident_delim = sequence(
        COMMON_ABBREVIATIONS,
        regex(r"\d+", Identifier),
        delim,
    )
    parser = many(type_ident_delim)

    # test that it parses the whole sequence
    assert parser("AHU1") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        TokenResult("1", Identifier("1"), 1),
    ]
    # no delimiter at the end, so it should not parse the whole thing
    assert parser("AHU1/SP2") == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        TokenResult("1", Identifier("1"), 1),
        TokenResult("/", Delimiter("/"), 1),
        TokenResult("SP", Constant(BRICK.Setpoint), 2),
        TokenResult("2", Identifier("2"), 1),
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


def test_parse():
    parser = sequence(
        abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK),
        regex(r"[/\-:_]+", Delimiter),
        regex(r"[0-9]+", Identifier),
    )
    result = parse(parser, "AHU-1")
    assert result.tokens == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3),
        TokenResult("-", Delimiter("-"), 1),
        TokenResult("1", Identifier("1"), 1),
    ], "Should parse the string"
    assert result.success, "Should parse the string"

    result = parse(parser, "AHU1-")
    assert result.tokens == [
        TokenResult("AHU", Constant(BRICK.Air_Handling_Unit), 3)
    ], "Should not parse all of the string"
    assert not result.success, "Should not parse the string"


def test_parse_list():
    parser = sequence(
        abbreviations(COMMON_EQUIP_ABBREVIATIONS_BRICK),
        regex(r"[/\-:_]+", Delimiter),
        regex(r"[0-9]+", Identifier),
    )
    points = [
        "AHU-1",
        "AHU1-",
        "FCU_2",
        "FCU-3",
        "4AHU",
    ]
    results, failed = parse_list(parser, points)
    assert len(results) == 3, "Should parse 3 of the points"
    assert len(failed) == 2, "Should fail to parse 2 of the points"


def test_first_true():
    # test that it returns the first true value
    assert first_true(["a", "b", "c"], pred=lambda x: x == "b") == "b"

    # test default value works
    assert (
        first_true(["a", "b", "c"], pred=lambda x: x == "d", default="default")
        == "default"
    )

    # test that it consumes the iterator
    values = iter(["abc", "def", "abd", "aef", "fgi", "lmno"])
    assert first_true(values, pred=lambda x: x.startswith("a")) == "abc"
    assert first_true(values, pred=lambda x: x.startswith("a")) == "abd"
    assert first_true(values, pred=lambda x: x.startswith("a")) == "aef"
    assert first_true(values, pred=lambda x: x.startswith("a")) is None
