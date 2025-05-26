from typing import List, Tuple, Optional, Set

from buildingmotif.label_parsing.tree import Node as PrefixTreeNode
from buildingmotif.label_parsing.tree import PrefixTreeCompressed
from buildingmotif.label_parsing.parser import Parser
from buildingmotif.label_parsing.combinators import (
    string as StringParser,  # Renamed to avoid conflict if a variable is named 'string'
    equip_abbreviations,
    point_abbreviations,
    delimiters,
    identifier,
)
from buildingmotif.label_parsing.tokens import Identifier as IdentifierToken


class ParserNode:
    """
    Represents a node in the derived parser tree.
    Each node encapsulates a parser and can have children representing subsequent parsing choices.
    """
    def __init__(self, parser: Optional[Parser], is_end: bool = False):
        # parser is Optional for the dummy root node
        self.parser = parser
        # is_end is True if a valid string can end after this parser matches
        self.is_end = is_end
        self.children: List[ParserNode] = []

    def add_child(self, child_node: 'ParserNode'):
        # Simple add for now. Deduplication might be needed if structure implies it.
        self.children.append(child_node)

    def __repr__(self, level=0):
        indent = "  " * level
        parser_repr = "DUMMY_ROOT" if self.parser is None else repr(self.parser)
        # Try to get a more specific name for known parser instances
        if self.parser is identifier:
            parser_repr = "Identifier"
        elif self.parser is delimiters:
            parser_repr = "Delimiters"
        elif self.parser is equip_abbreviations:
            parser_repr = "EquipAbbreviations"
        elif self.parser is point_abbreviations:
            parser_repr = "PointAbbreviations"
        elif isinstance(self.parser, StringParser):
            parser_repr = f"String({self.parser.s})"

        ret = f"{indent}- {parser_repr}" + (" (END)" if self.is_end else "") + "\n"
        for child in self.children:
            ret += child.__repr__(level + 1)
        return ret

    # For potential deduplication if complex merging logic is added later
    # For now, __eq__ and __hash__ are not strictly necessary with simple list append.
    def __eq__(self, other):
        if not isinstance(other, ParserNode):
            return NotImplemented
        # Structural equality check (can be complex if parsers are complex)
        # For now, identity of known parsers and type for others.
        # This is a simplified equality for demonstration.
        return (
            (self.parser is other.parser or isinstance(self.parser, type(other.parser))) and
            self.is_end == other.is_end and
            len(self.children) == len(other.children)  # Further check children recursively if needed
        )

    def __hash__(self):
        # Simplified hash. For complex structures, this needs care.
        return hash((id(self.parser) if self.parser else None, self.is_end, len(self.children)))


class ParserTreeBuilder:
    """
    Builds a tree of parsers from a PrefixTreeCompressed instance.
    Sibling nodes in the prefix tree that can be matched by the same general parser
    are merged under a single node representing that general parser in the output tree.
    """
    def __init__(self, prefix_tree: PrefixTreeCompressed):
        self.prefix_tree = prefix_tree
        # Order matters: more specific or common parsers could be tried first,
        # but current logic iterates and groups, so order is for tie-breaking if one edge matches multiple.
        # Here, it's about finding *any* general parser that applies to a set of edges.
        self.candidate_general_parsers: List[Parser] = [
            equip_abbreviations,
            point_abbreviations,
            delimiters,
            identifier,
        ]

    def _text_matches_parser_fully(self, text: str, parser: Parser) -> bool:
        """Checks if the given parser fully matches the text."""
        if not text:  # General parsers usually don't match empty strings
            return False

        result_tokens = parser(text)  # parser.__call__

        if not result_tokens or any(rt.error for rt in result_tokens):
            return False

        consumed_length = sum(rt.length for rt in result_tokens)
        return consumed_length == len(text)

    def build_tree(self) -> ParserNode:
        """
        Builds the parser tree from the initialized PrefixTreeCompressed.
        The root of the returned tree is a dummy node; its children are the
        first actual parsers in the derived structure.
        """
        # The root of our ParserNode tree is a conceptual starting point.
        # Its 'is_end' reflects if the empty string itself is a valid entry in the prefix tree.
        dummy_root_parser_node = ParserNode(None, self.prefix_tree.root.is_end_of_string)

        children_of_dummy_root = self._derive_parsers_for_outgoing_edges(self.prefix_tree.root)
        for child_node in children_of_dummy_root:
            dummy_root_parser_node.add_child(child_node)

        return dummy_root_parser_node

    def _derive_parsers_for_outgoing_edges(self, pt_node: PrefixTreeNode) -> List[ParserNode]:
        """
        Analyzes outgoing edges from a PrefixTreeNode, groups them by common parsers (merging),
        and recursively builds ParserNode children for these groups.
        """
        derived_parser_nodes: List[ParserNode] = []

        # Get all (edge_label, child_PrefixTreeNode) pairs
        outgoing_edges: List[Tuple[str, PrefixTreeNode]] = list(pt_node.children.values())

        # Keep track of PrefixTreeNodes that have been assigned to a general parser group
        # to avoid processing them again for specific string parsers.
        # We use the child_PrefixTreeNode as the key for processed status.
        processed_pt_children: Set[PrefixTreeNode] = set()

        # Phase 1: Try to group edges by candidate general parsers
        for general_parser in self.candidate_general_parsers:
            # Collect all edges from pt_node that match this general_parser
            # and whose corresponding child_PrefixTreeNode hasn't been processed yet.
            matching_edges_for_current_general_parser: List[Tuple[str, PrefixTreeNode]] = []
            for edge_label, child_pt_node in outgoing_edges:
                if child_pt_node not in processed_pt_children:
                    if self._text_matches_parser_fully(edge_label, general_parser):
                        matching_edges_for_current_general_parser.append((edge_label, child_pt_node))

            if matching_edges_for_current_general_parser:
                # Merge these edges under this general_parser
                # is_end is True if any path through this general_parser (for one of the matched edges)
                # can terminate here (i.e., the corresponding child_PrefixTreeNode is an end_of_string).
                is_end_for_group = any(
                    child_pt_n.is_end_of_string for _, child_pt_n in matching_edges_for_current_general_parser
                )
                group_parser_node = ParserNode(general_parser, is_end_for_group)

                # Recursively build children for this group_parser_node.
                # Each child_PrefixTreeNode in this group contributes to the children of group_parser_node.
                # The children of group_parser_node are the parsers that can follow general_parser
                # when it has matched one of the edge_labels in this group.
                children_for_group_node_set = {}  # Use dict as ordered set to avoid duplicates by (parser_type, is_end)
                # This simple dedupe might not be perfect for complex structures.

                for _, child_pt_node_in_group in matching_edges_for_current_general_parser:
                    processed_pt_children.add(child_pt_node_in_group)  # Mark as processed

                    # Recursively find parsers for edges outgoing from child_pt_node_in_group
                    sub_parsers = self._derive_parsers_for_outgoing_edges(child_pt_node_in_group)
                    for sp in sub_parsers:
                        # Simple deduplication based on (parser object, is_end status)
                        # Hashing ParserNode directly might be an issue if parsers are not consistently hashable.
                        # Using id(parser) for known instances, type for others.
                        key_parser_obj = sp.parser
                        parser_identity_key: Tuple
                        if key_parser_obj in self.candidate_general_parsers:
                            parser_identity_key = (id(key_parser_obj),)
                        elif isinstance(key_parser_obj, StringParser):  # For StringParser, include the string value
                            parser_identity_key = (type(key_parser_obj), key_parser_obj.s)
                        else:  # Fallback for other parser types
                            parser_identity_key = (type(key_parser_obj),)

                        key = (parser_identity_key, sp.is_end)
                        if key not in children_for_group_node_set:
                            children_for_group_node_set[key] = sp

                for sp_unique in children_for_group_node_set.values():
                    group_parser_node.add_child(sp_unique)

                derived_parser_nodes.append(group_parser_node)

        # Phase 2: Handle remaining edges with specific StringParser instances
        for edge_label, child_pt_node in outgoing_edges:
            if child_pt_node not in processed_pt_children:
                # This edge was not matched by any general parser group. Create a StringParser for it.
                # The type_name for StringParser is tricky. Using IdentifierToken as a default.
                specific_string_parser = StringParser(edge_label, IdentifierToken)

                # is_end is simply child_pt_node.is_end_of_string as this is a non-merged path.
                string_node = ParserNode(specific_string_parser, child_pt_node.is_end_of_string)

                # Recursively find parsers for edges outgoing from child_pt_node
                sub_parsers = self._derive_parsers_for_outgoing_edges(child_pt_node)
                for sp in sub_parsers:
                    string_node.add_child(sp)  # Deduplication could also be applied here if necessary

                derived_parser_nodes.append(string_node)
                # processed_pt_children.add(child_pt_node) # Mark, though it's the end of loop for this pt_node
        return derived_parser_nodes
