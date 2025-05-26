import pytest

from buildingmotif.label_parsing.tree import PrefixTreeCompressed
from buildingmotif.label_parsing.parser_tree_builder import ParserTreeBuilder, ParserNode
from buildingmotif.label_parsing.combinators import (
    string as StringParser,
    equip_abbreviations,
    point_abbreviations,
    delimiters,
    identifier,
)
# IdentifierToken is not directly asserted in these structural tests,
# but imported to acknowledge its use in ParserTreeBuilder.
from buildingmotif.label_parsing.tokens import Identifier as IdentifierToken


# Helper to find a specific child node in a ParserNode's children list
def find_child_parser_node(parent_node: ParserNode, parser_type_or_instance, parser_value_for_string=None):
    """
    Finds a child ParserNode that matches the given parser type/instance.

    :param parent_node: The ParserNode whose children to search.
    :param parser_type_or_instance: Either a specific parser instance (for singletons like 'identifier')
                                    or a class type (like StringParser).
    :param parser_value_for_string: If parser_type_or_instance is StringParser, this specifies the
                                    expected string value of the StringParser.
    :return: The matching child ParserNode, or None if not found.
    """
    # For singleton general parsers (checking by identity)
    if parser_type_or_instance in [identifier, delimiters, equip_abbreviations, point_abbreviations]:
        for child in parent_node.children:
            if child.parser is parser_type_or_instance:
                return child
    # For StringParser class (checking by type and optionally by string value)
    elif parser_type_or_instance is StringParser:
        for child in parent_node.children:
            if isinstance(child.parser, StringParser):
                if parser_value_for_string is None or child.parser.s == parser_value_for_string:
                    return child
    return None


def test_empty_input():
    pt = PrefixTreeCompressed([])
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert parser_root.parser is None  # Dummy root
    assert not parser_root.is_end  # Empty string not in tree by default
    assert len(parser_root.children) == 0


def test_empty_string_in_input():
    pt = PrefixTreeCompressed([""])
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert parser_root.parser is None
    assert parser_root.is_end  # Empty string IS in tree
    assert len(parser_root.children) == 0

    pt_with_others = PrefixTreeCompressed(["", "a"])
    builder_with_others = ParserTreeBuilder(pt_with_others)
    parser_root_with_others = builder_with_others.build_tree()

    assert parser_root_with_others.parser is None
    assert parser_root_with_others.is_end
    assert len(parser_root_with_others.children) == 1  # For "a"
    
    child_a = find_child_parser_node(parser_root_with_others, identifier) # "a" matches identifier
    assert child_a is not None
    assert child_a.is_end


def test_single_string_matches_identifier():
    pt = PrefixTreeCompressed(["abc"])
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert parser_root.parser is None and not parser_root.is_end
    assert len(parser_root.children) == 1

    child_node = parser_root.children[0]
    assert child_node.parser is identifier
    assert child_node.is_end
    assert len(child_node.children) == 0


def test_single_string_no_general_match():
    # "a-b" does not match default identifier regex fully, nor other general parsers
    pt = PrefixTreeCompressed(["a-b"])
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert parser_root.parser is None and not parser_root.is_end
    assert len(parser_root.children) == 1

    child_node = parser_root.children[0]
    assert isinstance(child_node.parser, StringParser)
    assert child_node.parser.s == "a-b"
    assert child_node.is_end
    assert len(child_node.children) == 0


def test_multiple_strings_no_merge_all_specific():
    strings = ["a-b", "c-d"]  # Neither matches a general parser
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 2

    node1 = find_child_parser_node(parser_root, StringParser, "a-b")
    assert node1 is not None and node1.is_end and len(node1.children) == 0

    node2 = find_child_parser_node(parser_root, StringParser, "c-d")
    assert node2 is not None and node2.is_end and len(node2.children) == 0


def test_merge_with_identifier():
    strings = ["idOne", "idTwo"]  # Both match identifier
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1
    merged_node = parser_root.children[0]
    assert merged_node.parser is identifier
    assert merged_node.is_end  # "idOne" and "idTwo" are ends
    assert len(merged_node.children) == 0


def test_merge_with_delimiter():
    strings = [":", "_", "-"]  # All match delimiters
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1
    merged_node = parser_root.children[0]
    assert merged_node.parser is delimiters
    assert merged_node.is_end
    assert len(merged_node.children) == 0


def test_merge_with_equip_abbreviations():
    strings = ["AHU", "FCU"]  # Both are equip abbreviations
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1
    merged_node = parser_root.children[0]
    assert merged_node.parser is equip_abbreviations
    assert merged_node.is_end
    assert len(merged_node.children) == 0


def test_merge_with_point_abbreviations():
    strings = ["ART", "TSP"]  # Both are point abbreviations
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1
    merged_node = parser_root.children[0]
    assert merged_node.parser is point_abbreviations
    assert merged_node.is_end
    assert len(merged_node.children) == 0


def test_mixed_merge_and_specific():
    strings = ["AHU", "id1", "x-y"]  # Equip, Identifier, Specific String
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 3

    equip_node = find_child_parser_node(parser_root, equip_abbreviations)
    assert equip_node is not None and equip_node.is_end and len(equip_node.children) == 0

    id_node = find_child_parser_node(parser_root, identifier)
    assert id_node is not None and id_node.is_end and len(id_node.children) == 0

    specific_node = find_child_parser_node(parser_root, StringParser, "x-y")
    assert specific_node is not None and specific_node.is_end and len(specific_node.children) == 0


def test_deeper_structure_branching_after_specific_string():
    strings = ["prefix_val1", "prefix_val2"]
    # PrefixTree: root -> "prefix_" -> "val1"(end), "val2"(end)
    # "prefix_" is a StringParser as it doesn't match general parsers.
    # "val1", "val2" merge into an Identifier parser.
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1
    
    prefix_node = find_child_parser_node(parser_root, StringParser, "prefix_")
    assert prefix_node is not None
    assert not prefix_node.is_end  # "prefix_" itself is not an inserted string
    assert len(prefix_node.children) == 1

    merged_id_node = prefix_node.children[0]
    assert merged_id_node.parser is identifier
    assert merged_id_node.is_end  # "val1" and "val2" (completing strings) are ends
    assert len(merged_id_node.children) == 0


def test_deeper_structure_merge_first_then_merge_second():
    strings = ["AHUval1", "FCUval2"]
    # PT: root -> "AHU" -> "val1"(e); root -> "FCU" -> "val2"(e)
    # ParserTree: Equip(AHU,FCU) -> Identifier(val1,val2)
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1
    
    equip_node = parser_root.children[0]
    assert equip_node.parser is equip_abbreviations
    assert not equip_node.is_end  # "AHU", "FCU" are not ends themselves
    assert len(equip_node.children) == 1

    id_node = equip_node.children[0]
    assert id_node.parser is identifier
    assert id_node.is_end  # "val1", "val2" (completing strings) are ends
    assert len(id_node.children) == 0


def test_is_end_distinction():
    strings = ["idA", "idAidB"]
    # PrefixTree: root -> "idA"(is_end=True) -> "idB"(is_end=True)
    # ParserTree: Identifier("idA", is_end=True) -> Identifier("idB", is_end=True)
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1
    
    node_idA = parser_root.children[0]
    assert node_idA.parser is identifier  # For "idA"
    assert node_idA.is_end  # "idA" is an inserted string
    assert len(node_idA.children) == 1  # For "idB"

    node_idB = node_idA.children[0]
    assert node_idB.parser is identifier  # For "idB"
    assert node_idB.is_end  # "idB" (completing "idAidB") is an inserted string
    assert len(node_idB.children) == 0


def test_deduplication_of_children_after_merge():
    strings = ["idA_common", "idB_common"]
    # PT: root -> "idA" -> "_common"(e); root -> "idB" -> "_common"(e)
    # ParserTree: Identifier(idA,idB) -> StringParser("_common")
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1
    
    merged_id_node = parser_root.children[0]
    assert merged_id_node.parser is identifier
    assert not merged_id_node.is_end  # "idA", "idB" are not ends themselves
    assert len(merged_id_node.children) == 1  # StringParser for "_common"

    common_suffix_node = merged_id_node.children[0]
    assert isinstance(common_suffix_node.parser, StringParser)
    assert common_suffix_node.parser.s == "_common"
    assert common_suffix_node.is_end
    assert len(common_suffix_node.children) == 0


def test_complex_scenario_multiple_merges_and_depth():
    strings = ["AHU1-DSP", "AHU1-HSP", "VAV2-DSP", "VAV2-CSP"]
    # Expected ParserTree:
    # Root (dummy)
    #   -> EquipAbbreviations (AHU, VAV) [is_end=F]
    #      -> Identifier (1, 2) [is_end=F]
    #         -> Delimiter (-) [is_end=F]
    #            -> PointAbbreviations (DSP, HSP, CSP) [is_end=T]
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert parser_root.parser is None and not parser_root.is_end
    assert len(parser_root.children) == 1

    pn_equip = parser_root.children[0]
    assert pn_equip.parser is equip_abbreviations and not pn_equip.is_end
    assert len(pn_equip.children) == 1

    pn_id = pn_equip.children[0]
    assert pn_id.parser is identifier and not pn_id.is_end
    assert len(pn_id.children) == 1

    pn_delim = pn_id.children[0]
    assert pn_delim.parser is delimiters and not pn_delim.is_end
    assert len(pn_delim.children) == 1

    pn_point = pn_delim.children[0]
    assert pn_point.parser is point_abbreviations and pn_point.is_end
    assert len(pn_point.children) == 0

def test_no_merge_if_subsequent_paths_differ_significantly():
    # If "AHU" is followed by "val1" and "FCU" by "otherVal",
    # they should still merge at EquipAbbreviations, but children will differ.
    strings = ["AHUval1", "FCUotherVal"]
    pt = PrefixTreeCompressed(strings)
    builder = ParserTreeBuilder(pt)
    parser_root = builder.build_tree()

    assert len(parser_root.children) == 1 # EquipAbbreviations for AHU, FCU
    
    equip_node = parser_root.children[0]
    assert equip_node.parser is equip_abbreviations
    assert not equip_node.is_end
    # Expect two children because "val1" and "otherVal" are different identifiers
    # and will lead to two distinct Identifier parser nodes under equip_node.
    # The current deduplication key includes the parser object (or type+value for StringParser).
    # Since 'val1' and 'otherVal' are different strings, they will result in different
    # StringParser(value) if not matched by identifier, or different paths if they do.
    # If both match 'identifier', they are still distinct paths from the prefix tree perspective
    # leading to this point. The deduplication in _derive_parsers_for_outgoing_edges
    # for children_for_group_node_set uses a key based on the sub-parser's identity.
    # If "val1" and "otherVal" both become `identifier` nodes, they are the same parser object.
    # Let's trace:
    # equip_node processes "AHU" and "FCU".
    # For "AHU", child_pt_node leads to "val1". _derive_parsers_for_outgoing_edges("val1") -> [ParserNode(identifier, is_end=T)]
    # For "FCU", child_pt_node leads to "otherVal". _derive_parsers_for_outgoing_edges("otherVal") -> [ParserNode(identifier, is_end=T)]
    # The key for dedupe is (id(identifier), True). So they are identical.
    assert len(equip_node.children) == 1

    id_node = equip_node.children[0]
    assert id_node.parser is identifier
    assert id_node.is_end
    assert len(id_node.children) == 0
