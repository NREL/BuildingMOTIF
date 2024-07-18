import importlib.util
import os
import re

from buildingmotif.label_parsing.build_parser import (
    generate_parsers_for_clusters,
    generate_parsers_for_points,
)
from buildingmotif.label_parsing.combinators import (
    COMMON_EQUIP_ABBREVIATIONS_BRICK,
    COMMON_POINT_ABBREVIATIONS,
    COMMON_GENERATED_ABBREVIATIONS
)
from buildingmotif.label_parsing.tools import abbreviationsTool, codeLinter


class ParserBuilder:

    def __init__(
        self,
        filename: str,
        col_name: str,
        num_tries=3,
        list_of_dicts=[COMMON_EQUIP_ABBREVIATIONS_BRICK, COMMON_POINT_ABBREVIATIONS],
    ):
        """
Initializes a new ParserBuilder object.

:param filename: File path to the CSV file.
:type filename: str
:param col_name: Name of the column where the point label data is stored.
:type col_name: str
:param num_tries: Maximum number of attempts for LLM to generate LLM_Token_Predictions object. Defaults to 3.
:type num_tries: int, optional
:param list_of_dicts: List of dictionaries mapping abbreviations to brick classes. Defaults to [equip_abbreviations, point_abbreviations].
:type list_of_dicts: List, optional
        """

        filename = os.path.abspath(filename)
        self.list_of_dicts = list_of_dicts
        try:
            (
                self.parsers,
                self.clusters,
                self.distance_metrics,
                self.clustering_metrics,
                self.flagged_abbreviations,
            ) = generate_parsers_for_clusters(
                filename, col_name, num_tries, list_of_dicts
            )
        except (
            ValueError
        ):  # if not enough points to cluster, generate parsers for each point
            self.parsers, self.clusters, self.flagged_abbreviations = (
                generate_parsers_for_points(
                    filename, col_name, num_tries, list_of_dicts
                )
            )
            self.distance_metrics, self.clustering_metrics = {}, {}

    def combine_parsers_and_get_metrics(self):
        """
Emits a ParserMetrics object which contains serialized parsers and parser metrics.
        """
        return ParserMetrics(self.parsers, self.clusters, self.list_of_dicts)

    def write_to_directory(self, directory: str):
        """
        Writes each parser and cluster to a file along with necessary imports.
        Saves in specified directory.

        :param directory: Directory path where each file containing a parser and its cluster will be saved.
        :type directory: str

        :return: None
        :rtype: None
        """

        if not os.path.exists(directory):
            os.makedirs(directory)

        for parser, cluster in zip(self.parsers, self.clusters):
            pattern = re.compile(r"([^\s]+)")
            parser_var = pattern.match(parser)[0]
            filename = parser_var + ".py"
            with open(os.path.join(directory, filename), "w") as file:
                file.write(
                    """
from buildingmotif.label_parsing.combinators import *
from buildingmotif.label_parsing.parser import parser_on_list
from buildingmotif.label_parsing.tools import abbreviationsTool
import rdflib
                    """
                )
                file.write(
                    f"""
COMBINED_ABBREVIATIONS = abbreviationsTool.make_combined_abbreviations({self.list_of_dicts})
                    """
                )
                file.write(
                    f"""
{parser}"""
                )
                file.write(
                    f"""
cluster = {cluster}"""
                )
            codeLinter._run(os.path.join(directory, filename))


class ParserMetrics:

    def __init__(self, parsers, clusters, list_of_dicts):
        """
Initializes a new ParserMetrics object.

:param parsers: List of parsers from ParserBuilder class.
:type parsers: List[str]
:param clusters: List of clusters from ParserBuilder class.
:type cluster: List[str]
:param list_of_dicts: provided list of abbreviation dictionaries passed to ParserBuilders
:type list_of_dicts: List[dict]
        """
        self.parsed_count = 0
        self.unparsed_count = 0
        self.total_count = 0
        self.serializers_list = []
        self.combined_clusters = []

        for parser, cluster in zip(parsers, clusters):
            clustered_info = {}
            try:
                temp_filename = os.path.join(os.getcwd(), "temp_parser.py")

                with open(
                    temp_filename, mode="w"
                ) as temp_file:  # using tempfile library writes file in /appdata directory, dependencies difficult to manage
                    pattern = re.compile(r"([^\s]+)")
                    parser_var = pattern.match(parser)[
                        0
                    ]  # matches the parser variable (e.g. parser_lencluster_11_417)
                    temp_file.write(
                        """
from buildingmotif.label_parsing.combinators import *
from buildingmotif.label_parsing.tools import abbreviationsTool
from buildingmotif.label_parsing.parser import parser_on_list
from buildingmotif.api.serializers import parser as serializerTool
import rdflib
                        """
                    )
                    temp_file.write(
                        f"""
COMBINED_ABBREVIATIONS = abbreviationsTool.make_combined_abbreviations({list_of_dicts})
                    """
                    )
                    temp_file.write(
                        f"""
{parser}"""
                    )
                    temp_file.write(
                        f"""
def get_serialization():
    return serializerTool.serialize({parser_var})"""
                    )
                    temp_file.write(
                        f"""
cluster = {cluster}"""
                    )
                    temp_file.write(
                        f"""
def run_parser():
    parsed, parsed_elements, unparsed, right, wrong = parser_on_list({parser_var}, cluster)
    return parsed, parsed_elements, unparsed, right, wrong"""
                    )

                # Load the module from the temporary file dynamically
                spec = importlib.util.spec_from_file_location(
                    "generated", temp_filename
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Call the function defined in the module to get parsed results, unparsed elements, and total parsed/unparsed
                parsed_arr, parsed_elements, unparsed_arr, right, wrong = (
                    module.run_parser()
                )
                serialized = module.get_serialization() 
                """
                serialization process is not a direct result of the parser generation process, 
                must be dynamically ran since parsers are strings
                """
                self.serializers_list.append(serialized)
                self.parsed_count += right
                self.unparsed_count += wrong
                self.total_count += right + wrong
                clustered_info["serialized_parser"] = serialized
                clustered_info["source_code"] = parser
                clustered_info["parsed_labels"] = parsed_elements
                clustered_info["unparsed_labels"] = unparsed_arr
                clustered_info["tokens"] = parsed_arr
                clustered_info["parser_metrics"] = {
                    "parsed_count": right,
                    "unparsed_count": wrong,
                    "total_count": right + wrong,
                }
                self.combined_clusters.append(clustered_info)
                

            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)  # remove file when complete