import re
from collections import defaultdict, namedtuple
from typing import List, Optional, Set

from rdflib import Graph

from buildingmotif.embeddings import Embedding
from buildingmotif.label_parsing.combinators import (
    choice,
    delimiters,
    equip_abbreviations,
    guess_embedding,
    identifier,
    point_abbreviations,
    sequence,
)
from buildingmotif.label_parsing.parser import Parser
from buildingmotif.label_parsing.tokens import Constant


class Node:
    """
    Represents a node in the Compressed Prefix Tree.
    Children are stored in a dictionary mapping the first element of an edge sequence
    to a tuple: (full_edge_label_sequence, child_Node_object).
    """

    def __init__(self):
        self.children = {}  # str_element -> (List[str]_label, Node)
        self.is_end_of_string = False
        # The "common sequence" to all children of this node is the
        # concatenation of edge label sequences from the root leading to this node.


class ParserMap:
    """
    Stores a mapping of a parser to the sequences it can parse.
    """

    def __init__(self):
        self.parser_to_sequences = []

    def __iter__(self):
        """
        Returns an iterator over the parser to sequences mapping.
        """
        return iter(self.parser_to_sequences)

    def __len__(self):
        """
        Returns the number of parsers in the map.
        """
        return len(self.parser_to_sequences)

    def addN(self, parser: Parser, sequences: set[str]):
        """
        Adds a parser and the set of sequences it can parse to the map.
        If the parser already exists, it merges the sequences.
        """
        for existing_parser, existing_sequences in self.parser_to_sequences:
            if existing_parser == parser:
                existing_sequences.update(sequences)
                return
        self.parser_to_sequences.append((parser, sequences))

    def add(self, parser: Parser, sequence: str):
        """
        Adds a parser and a single sequence it can parse to the map.
        If the parser already exists, it merges the sequence.
        """
        for existing_parser, existing_sequences in self.parser_to_sequences:
            if existing_parser == parser:
                existing_sequences.add(sequence)
                return
        self.parser_to_sequences.append((parser, {sequence}))

    def parser_for(self, sequence: str) -> Parser:
        """
        Returns the parser that can parse the given sequence.
        If no such parser exists, returns None.
        """
        for parser, sequences in self.parser_to_sequences:
            if sequence in sequences:
                return parser
        return None

    def sequences_for(self, parser: Parser) -> set[str]:
        """
        Returns the set of sequences that can be parsed by the given parser.
        If no such parser exists, returns an empty set.
        """
        for existing_parser, sequences in self.parser_to_sequences:
            if existing_parser == parser:
                return sequences
        return set()

    def dump(self):
        """
        Prints a string representation of the parser map.
        """
        for parser, sequences in self.parser_to_sequences:
            print(f"Parser: {parser}")
            for seq in sequences:
                print(f"  - {seq}")


CursorChild = namedtuple("CursorChild", ["label", "node"])


class PrefixTreeCursor:
    def __init__(self, tree: "PrefixTreeCompressed"):
        """
        Initializes the cursor for the PrefixTreeCompressed.

        Args:
            tree (PrefixTreeCompressed): The tree to create a cursor for.
        """
        self.tree = tree
        self.current_node = tree.root
        self.current_sequence = []

    def reset(self):
        """
        Resets the cursor to the root of the tree.
        """
        self.current_node = self.tree.root
        self.current_sequence = []

    def current_sequence_str(self) -> str:
        """
        Returns the current sequence as a string.
        """
        return "".join(self.current_sequence)

    def children(self) -> list[CursorChild]:
        """
        Returns a list of tuples (edge_label_sequence, child_node) for the current node's children.
        """
        return [
            CursorChild(label=label_seq, node=child_node)
            for label_seq, child_node in self.current_node.children.values()
        ]

    def child_labels(self) -> list[list[str]]:
        """
        Returns a list of edge label sequences for the current node's children.
        """
        return [label_seq for label_seq, _ in self.current_node.children.values()]

    def child_labels_str(self) -> list[str]:
        """
        Returns a list of edge label sequences for the current node's children.
        """
        return [
            "".join(label_seq) for label_seq, _ in self.current_node.children.values()
        ]

    def move_to_child(self, edge_label_sequence: list[str]):
        """
        Moves the cursor to a child node based on the given edge label sequence.

        Args:
            edge_label_sequence (List[str]): The edge label sequence to move to.

        Returns:
            bool: True if the move was successful, False if no such child exists.
        """
        for first_element, (
            label_seq,
            child_node,
        ) in self.current_node.children.items():
            if label_seq == edge_label_sequence:
                self.current_node = child_node
                self.current_sequence += label_seq
                return True
        return False

    def move_to_child_str(self, edge_label_sequence: str):
        """
        Moves the cursor to a child node based on the given edge label sequence string.

        Args:
            edge_label_sequence (str): The edge label sequence to move to.

        Returns:
            bool: True if the move was successful, False if no such child exists.
        """
        for first_element, (
            label_seq,
            child_node,
        ) in self.current_node.children.items():
            if "".join(label_seq) == edge_label_sequence:
                self.current_node = child_node
                self.current_sequence += label_seq
                return True
        return False

    def find_bfs(self, search_str: str):
        """
        moves the cursor to the first child (edge label sequence) that matches the search_str.
        """
        from collections import deque

        queue = deque([(self.tree.root, [])])
        while queue:
            current_node, current_sequence = queue.popleft()
            for first_element, (label_seq, child_node) in current_node.children.items():
                if "".join(label_seq) == search_str:
                    self.current_node = child_node
                    self.current_sequence = current_sequence + label_seq
                    return True
                queue.append((child_node, current_sequence + label_seq))
        return False


class PrefixTreeCompressed:
    """
    A Compressed Prefix Tree (related to Radix Tree/Patricia Trie).
    Edges can represent sequences of strings.
    """

    def __init__(self, sequences_list=None):
        """
        Initializes the PrefixTree.
        Optionally populates it with an initial list of string sequences.

        Args:
            sequences_list (list, optional): A list of string sequences (List[List[str]])
                                             to add to the tree. Defaults to None.
        """
        self.root = Node()
        if sequences_list:
            for s in sequences_list:
                self.insert(s)

    def insert(self, sequence: list[str]):
        """
        Inserts a sequence of strings into the compressed prefix tree.

        Args:
            sequence (List[str]): The sequence of strings to insert.
        """
        if not isinstance(sequence, list) or not all(
            isinstance(item, str) for item in sequence
        ):
            raise TypeError("Input must be a list of strings.")
        if not sequence:  # Handle empty sequence case explicitly
            self.root.is_end_of_string = True
            return
        self._insert_recursive(self.root, sequence)

    def _insert_recursive(self, current_node: Node, sequence_to_insert: list[str]):
        """
        Recursive helper to insert a sequence of strings.

        Args:
            current_node (Node): The node to insert from.
            sequence_to_insert (List[str]): The remaining part of the sequence to insert.
        """
        if not sequence_to_insert:
            return

        first_element_of_sequence = sequence_to_insert[0]

        if first_element_of_sequence in current_node.children:
            edge_label_seq, child_node = current_node.children[
                first_element_of_sequence
            ]

            lcp_len = 0
            while (
                lcp_len < len(sequence_to_insert)
                and lcp_len < len(edge_label_seq)
                and sequence_to_insert[lcp_len] == edge_label_seq[lcp_len]
            ):
                lcp_len += 1

            if lcp_len == len(edge_label_seq):
                remaining_sequence_after_edge = sequence_to_insert[lcp_len:]
                if not remaining_sequence_after_edge:
                    child_node.is_end_of_string = True
                self._insert_recursive(child_node, remaining_sequence_after_edge)
            else:
                common_prefix_part = edge_label_seq[:lcp_len]
                suffix_of_old_edge = edge_label_seq[lcp_len:]
                suffix_of_new_sequence = sequence_to_insert[lcp_len:]

                intermediate_node = Node()
                # The key remains the first element of the original edge_label_seq,
                # which is also the first element of common_prefix_part.
                current_node.children[first_element_of_sequence] = (
                    common_prefix_part,
                    intermediate_node,
                )

                # The original child_node (and its subtree) becomes a child of intermediate_node,
                # reached by the suffix_of_old_edge.
                # Ensure suffix_of_old_edge is not empty before using its first element as key.
                if suffix_of_old_edge:
                    intermediate_node.children[suffix_of_old_edge[0]] = (
                        suffix_of_old_edge,
                        child_node,
                    )
                else:  # This case should ideally not happen if lcp_len < len(edge_label_seq)
                    # If it does, it implies child_node itself is the intermediate_node.
                    # For safety, if suffix_of_old_edge is empty, child_node's properties (like is_end_of_string)
                    # should be merged into intermediate_node if it represents the same point.
                    # However, current logic: if lcp_len < len(edge_label_seq), suffix_of_old_edge is non-empty.
                    pass

                if not suffix_of_new_sequence:
                    intermediate_node.is_end_of_string = True
                else:
                    new_branch_node = Node()
                    new_branch_node.is_end_of_string = True
                    intermediate_node.children[suffix_of_new_sequence[0]] = (
                        suffix_of_new_sequence,
                        new_branch_node,
                    )
        else:
            new_child = Node()
            new_child.is_end_of_string = True
            current_node.children[first_element_of_sequence] = (
                sequence_to_insert,
                new_child,
            )

    def search(self, sequence: list[str]) -> bool:
        """
        Checks if a complete sequence of strings exists in the tree.

        Args:
            sequence (List[str]): The sequence to search for.

        Returns:
            bool: True if the sequence exists as a complete entry, False otherwise.
        """
        if not sequence:  # Search for empty sequence
            return self.root.is_end_of_string

        current_node = self.root
        remaining_sequence = sequence
        while remaining_sequence:
            first_element = remaining_sequence[0]
            if first_element not in current_node.children:
                return False

            edge_label_seq, child_node = current_node.children[first_element]

            if (
                len(remaining_sequence) >= len(edge_label_seq)
                and remaining_sequence[: len(edge_label_seq)] == edge_label_seq
            ):
                remaining_sequence = remaining_sequence[len(edge_label_seq) :]
                current_node = child_node
            else:
                return False

        return current_node.is_end_of_string

    def starts_with(self, prefix_sequence: list[str]) -> bool:
        """
        Checks if any sequence in the tree starts with the given prefix sequence.

        Args:
            prefix_sequence (List[str]): The prefix sequence to check.

        Returns:
            bool: True if there's at least one sequence with this prefix, False otherwise.
        """
        if not prefix_sequence:
            return True

        current_node = self.root
        remaining_prefix = prefix_sequence
        while remaining_prefix:
            first_element = remaining_prefix[0]
            if first_element not in current_node.children:
                return False

            edge_label_seq, child_node = current_node.children[first_element]

            if (
                len(remaining_prefix) >= len(edge_label_seq)
                and remaining_prefix[: len(edge_label_seq)] == edge_label_seq
            ):
                remaining_prefix = remaining_prefix[len(edge_label_seq) :]
                current_node = child_node
            elif (
                len(edge_label_seq) >= len(remaining_prefix)
                and edge_label_seq[: len(remaining_prefix)] == remaining_prefix
            ):
                return True
            else:
                return False
        return True

    def get_all_strings(self) -> list[list[str]]:
        """
        Retrieves all complete sequences of strings stored in the tree.

        Returns:
            List[List[str]]: A list of all sequences in the tree.
        """
        sequences: list[list[str]] = []
        self._collect_strings_recursive(self.root, [], sequences)
        if self.root.is_end_of_string and [] not in sequences:  # Handle empty sequence
            sequences.append([])
        # Sort for consistent output, ensuring lists are comparable (tuples for sorting)
        return sorted(sequences, key=lambda x: tuple(x))

    def _collect_strings_recursive(
        self,
        node: Node,
        current_prefix_sequence: list[str],
        sequences_list: list[list[str]],
    ):
        """Helper recursive function to collect all sequences."""
        if node.is_end_of_string:
            sequences_list.append(list(current_prefix_sequence))  # Add a copy

        for _first_element, (edge_label_seq, child_node) in sorted(
            node.children.items()
        ):
            self._collect_strings_recursive(
                child_node, current_prefix_sequence + edge_label_seq, sequences_list
            )

    def print_tree_structure(self):
        """
        Prints a visual representation of the compressed tree structure.
        - Each printed line starting with '-' shows an edge label sequence.
        - A '(*)' indicates that the path from ROOT ending with this edge label sequence
          forms a complete sequence.
        - The path from ROOT to any node (formed by concatenating edge label sequences)
          is the common prefix sequence for all sequences passing through that node's children edges.
        """
        print("Compressed Prefix Tree Structure:")
        root_marker = " (*)" if self.root.is_end_of_string else ""
        print(f"ROOT{root_marker}")
        self._print_node_recursive(self.root, 1)

    def _print_node_recursive(self, parent_node_obj: Node, level: int):
        indent = "  " * level
        for _first_char, (edge_label_seq, child_node_obj) in sorted(
            parent_node_obj.children.items()
        ):
            marker = " (*)" if child_node_obj.is_end_of_string else ""
            print(f"{indent}- {edge_label_seq}{marker}")
            self._print_node_recursive(child_node_obj, level + 1)


def split_bms_string(s: str) -> list[str]:
    """
    Splits an input string 's' into a list of strings based on specific delimiters:
    - ':', '_', '.', '-', ' ' and '/' (these are their own token)
    - character class transition (alphabetic to numeric or vice versa)
    - lowercase to uppercase transition
    """
    # Define the regular expression pattern for splitting.
    pattern = (
        r"([:_\.\- /\n])|"  # Match individual delimiters ':', '_', '.', '-', ' ', '/', and '\n'
        r"(?<=[a-z])(?=[A-Z])|"  # Match transition from lowercase to uppercase
        r"(?<=[A-Za-z])(?=[0-9])|"  # Match transition from alphabetic to numeric
        r"(?<=[0-9])(?=[A-Za-z])"  # Match transition from numeric to alphabetic
    )

    # Use re.split to split the string based on the pattern.
    parts = re.split(pattern, s)

    # Filter out any None or empty strings resulted from re.split
    return [p for p in parts if p is not None and p != ""]


def get_string_sequences(str_list: list[str]) -> list[list[str]]:
    sequences = [
        split_bms_string(s.strip()) for s in str_list if isinstance(s, str) and s.strip()
    ]
    # filter out empty strings in the sequences
    return [list(filter(None, seq)) for seq in sequences if seq]


brick = Graph().parse("https://brickschema.org/schema/1.4/Brick.ttl")
emb = Embedding(brick)

brick_point_guess = guess_embedding(emb, Constant, threshold=0.7)
known_parsers = [
    equip_abbreviations,
    point_abbreviations,
    delimiters,
    brick_point_guess,
    identifier,
]


# def guess_parser_str(seq: str) -> tuple[str, Parser]:
#    """
#    Main function that initiates the backtracking search to find
#    a parser that can parse some prefix of the string, and returns
#    the rest of the string along with the parser.
#    """
#    def parse_with_backtracking(seq: str, parser_stack: list) -> tuple[str, Parser]:
#        """
#        Recursive helper function to try parsing with backtracking.
#        """
#        if not seq:
#            return seq, sequence(*parser_stack)
#
#        seq_parser = sequence(*parser_stack)
#        result = seq_parser(seq)
#        errored = any(r.error for r in result)
#        consumed_length = sum([r.length for r in result])
#
#        if not errored and consumed_length > 0:
#            return seq[consumed_length:], seq_parser
#
#        for parser in known_parsers:
#            result = parser(seq)
#            consumed_length = sum([r.length for r in result])
#            errored = any(r.error for r in result)
#            if errored or consumed_length == 0:
#                continue
#
#            consumed_length = sum([r.length for r in result])
#            remaining = seq[consumed_length:]
#            new_stack = parser_stack + [parser]
#            remaining, parser = parse_with_backtracking(remaining, new_stack)
#
#            if remaining is not None:
#                return remaining, parser
#
#        return None, None
#
#    final_remaining, final_parser = parse_with_backtracking(seq, [])
#    print(f"Final remaining string: {final_remaining}")
#    print(f"Final parser: {final_parser}")
#    if final_remaining is not None:
#        return final_remaining, final_parser
#    else:
#        raise ValueError("No suitable parser found.")


def guess_parser_str(str_set: set[str]) -> "ParserMap":
    """
    Main function that initiates the backtracking search to find
    a parser that can parse prefixes of strings in the set, and returns
    the rest of the strings along with the common parser.
    """

    def parse_with_backtracking(seq: str, parser_stack: list) -> tuple[str, Parser]:
        """
        Recursive helper function to try parsing with backtracking.
        """
        if not seq:
            # print(f"Empty sequence reached, returning parser stack: {parser_stack}")
            return seq, sequence(*parser_stack)

        seq_parser = sequence(*parser_stack)
        result = seq_parser(seq)
        errored = any(r.error for r in result)
        consumed_length = sum([r.length for r in result])

        if not errored and consumed_length > 0:
            return seq[consumed_length:], seq_parser

        for parser in known_parsers:
            result = parser(seq)
            consumed_length = sum([r.length for r in result])
            errored = any(r.error for r in result)
            if errored or consumed_length == 0:
                continue
            # print(f"Accepted parser: {parser}, consumed_length: {consumed_length}, errored: {errored} {seq}")

            remaining = seq[consumed_length:]
            new_stack = parser_stack + [parser]
            remaining, parser = parse_with_backtracking(remaining, new_stack)

            if remaining is not None:
                return remaining, parser

        return None, None

    # track which sequences are successfully parsed by which parsers
    # stores the parser and the set of strings (sequences) it can parse
    seq2parser: ParserMap = ParserMap()

    for seq in str_set:
        _, possible_parser = parse_with_backtracking(seq, [])
        if possible_parser is None:
            print(f"Sequence {seq} could not be parsed with any parser.")
            continue
        # check if the parser is already in the list
        seq2parser.add(possible_parser, seq)

        # If this is the first successful parser, record it as final_parser
        # if possible_parser and final_parser is None:
        #    final_parser = possible_parser
        #    final_remaining_set.remove(seq)

        # If there's a parser and it matches the previous one, continue
        # elif possible_parser == final_parser:
        #    final_remaining_set.remove(seq)

        # else:
        #    # If you find a sequence that does not fit the common parser
        #    # and backtracking search does not yield a parser, remark appropriately
        #    print(f"Sequence {seq} could not be parsed with the current parser stack: {final_parser}")
        #    raise ValueError(f"No suitable common parser found for sequence: {seq}")
    return seq2parser

    # Return the set of unparsed strings and the common parser
    # print(f"Final remaining strings: {final_remaining_set}")
    # print(f"Common Parser: {final_parser}")

    # if final_parser:
    #    return final_remaining_set, final_parser
    # else:
    #    raise ValueError("No suitable common parser found.")


class PTNode:
    """
    Represents a node in the ParserTree.
    Each node encapsulates a parser that describes the transition from its parent,
    and can have children representing subsequent parsing choices.
    """

    def __init__(self, parser: Optional[Parser], is_end: bool = False):
        self.parser = parser  # Parser for the edge leading to this node
        self.children: list[PTNode] = []
        self.is_end = is_end  # True if using this parser can complete a sequence

    def add_child(self, child_node: "PTNode"):
        self.children.append(child_node)


class ParserTree:
    """
    Builds a tree of parsers based on a PrefixTreeCompressed.
    It groups edge labels in the PrefixTreeCompressed by common parsers
    and constructs a new tree representing these parsing relationships.
    """

    def __init__(self, prefix_tree: PrefixTreeCompressed):
        self.root = PTNode(parser=None, is_end=prefix_tree.root.is_end_of_string)
        self._build_recursive([prefix_tree.root], self.root)

    def _build_recursive(self, p_nodes: List[Node], pt_parent: PTNode):
        # p_nodes: List of PrefixTreeCompressed.Node objects whose children we are currently processing.
        # pt_parent: The ParserTree.PTNode to which new children (representing common parsers) will be added.

        aggregated_children_map = defaultdict(list)
        all_child_labels_str: Set[str] = set()

        for p_node in p_nodes:
            for edge_label_seq, child_p_node_obj in p_node.children.values():
                edge_label_str = "".join(edge_label_seq)
                all_child_labels_str.add(edge_label_str)
                aggregated_children_map[edge_label_str].append(child_p_node_obj)

        if not all_child_labels_str:
            return

        parser_map_for_children = guess_parser_str(all_child_labels_str)

        for common_parser, parsed_edge_labels_set in parser_map_for_children:
            if common_parser is None:
                # This case should be handled if guess_parser_str can return None for a parser
                # For now, assume common_parser is always a valid Parser object
                continue

            is_this_parser_terminal = False
            next_level_p_nodes_for_this_parser: List[Node] = []

            for edge_label_str in parsed_edge_labels_set:
                children_p_nodes_for_label = aggregated_children_map[edge_label_str]
                for child_p_node in children_p_nodes_for_label:
                    if child_p_node.is_end_of_string:
                        is_this_parser_terminal = True
                    next_level_p_nodes_for_this_parser.append(child_p_node)

            new_pt_child_node = PTNode(
                parser=common_parser, is_end=is_this_parser_terminal
            )
            pt_parent.add_child(new_pt_child_node)

            if next_level_p_nodes_for_this_parser:
                # Deduplicate nodes for the next level to avoid redundant processing if multiple paths converge
                # Hashing Node objects might be an issue if they are not inherently hashable
                # A simple list of unique objects can be achieved by checking presence before adding,
                # but for now, passing potentially duplicate nodes is handled by defaultdict in the next call.
                # For simplicity and correctness, ensure unique nodes are passed if performance becomes an issue.
                # However, the current logic of `aggregated_children_map` naturally handles this grouping.
                self._build_recursive(
                    next_level_p_nodes_for_this_parser, new_pt_child_node
                )

    def print_tree(self):
        """Prints a visual representation of the ParserTree structure."""
        print("ParserTree Structure:")
        self._print_pt_node_recursive(self.root, 0)

    def _print_pt_node_recursive(self, pt_node: PTNode, level: int):
        indent = "  " * level
        parser_str = str(pt_node.parser) if pt_node.parser else "ROOT"
        end_marker = " (*)" if pt_node.is_end else ""
        print(f"{indent}- Parser: {parser_str}{end_marker}")
        for child_pt_node in pt_node.children:
            self._print_pt_node_recursive(child_pt_node, level + 1)

    def to_parser(self) -> Parser:
        """
        Returns a parser that represents the entire ParserTree.
        """
        parsers = []  # a 'sequence' of parsers that can parse the tree
        stack = [self.root]
        # bfs through the tree to construct a parser
        while stack:
            child_parsers = [node.parser for node in stack if node.parser]
            if not child_parsers:
                # If no parsers are found in the current layer, we can skip this layer
                stack = [child for node in stack for child in node.children]
                continue
            # if there's only 1 child, then extend the parsers list with it
            layer_parsers = [unpack_sequence(p) for p in child_parsers]
            if len(child_parsers) == 1:
                parsers.extend(sum(layer_parsers, []))
                stack = [child for node in stack for child in node.children]
                continue
            # if more than 1 child parser, then we need to create a choice parser
            # each child parser is a sequence of parsers.
            choice_parsers = [sequence(*p) for p in layer_parsers]
            parsers.append(choice(*choice_parsers))
            stack = [child for node in stack for child in node.children]
        return sequence(*parsers)


def unpack_sequence(p: Parser) -> list[Parser]:
    # unpacks a 'sequence' Parser into a list of parsers
    if isinstance(p, sequence):
        return sum([unpack_sequence(child_parser) for child_parser in p.parsers], [])
    return [p]  # If it's not a sequence, return it as a single-item list


# --- Example Usage ---
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        point_file = sys.argv[1]
        with open(point_file, "r") as f:
            # skip the first line if it contains headers
            f.readline()
            raw_string_data = f.readlines()
    else:
        raw_string_data = [
            ":BuildingName_02:FCU503_ChwVlvPos",
            ":BuildingName_01:FCU336_OccHtgSptFnl",
            ":BuildingName_02:FCU510_EffOcc",
            ":BuildingName_02:FCU507_UnoccHtgSpt",
            ":BuildingName_02:FCU415_UnoccHtgSpt",
            ":BuildingName_01:FCU203_OccClgSpt",
            ":BuildingName_02:FCU521_UO11_HwVlvOut",
            ":BuildingName_01:FCU365_UnoccHtgSptFnl",
            ":BuildingName_02:FCU529_UnoccHtgSpt",
            ":BuildingName_01:FCU243_EffOcc",
            ":BuildingName_01:FCU362_ChwVlvPos",
            ":BuildingName_01:FCU180B_UnoccClgSptFnl",
            ":BuildingName_02:FCU539_UO12_ChwVlvOut",
        ]

    sequence_data = get_string_sequences(raw_string_data)

    print("Constructing Compressed Prefix Tree with initial sequence data...")
    prefix_tree = PrefixTreeCompressed(sequence_data)
    print("Construction complete.\n")

    prefix_tree.print_tree_structure()
    print("\n" + "=" * 50 + "\n")

    # cursor = PrefixTreeCursor(prefix_tree)
    # child = cursor.children()[0]
    # cursor.move_to_child(child.label)
    # print(cursor.current_sequence)
    # print(guess_parser_str([cursor.current_sequence_str()]))
    # print(guess_parser_str(cursor.child_labels_str()))
    # cursor.move_to_child(cursor.child_labels()[0])
    # print(cursor.child_labels_str())
    # print(guess_parser_str(cursor.child_labels_str()))

    print("\nConstructing ParserTree from PrefixTreeCompressed...")
    parser_tree = ParserTree(prefix_tree)
    print("ParserTree construction complete.\n")
    parser_tree.print_tree()
    parser = parser_tree.to_parser()
    print(f"\nParser for the entire tree: {parser}")
    for seq in raw_string_data:
        print(parser(seq))
