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
)
from buildingmotif.label_parsing.tools import abbreviationsTool, codeLinter


class SerializedParserMetrics:
    """
    Combines parsers into a compact class with detailed metrics and other information.
    Allows for easier serialization.

    Attributes:
        parsers(List[str]): list of all parsers
        serializers_list (List[Dict]): list of all serialized parsers
        clusters(List[List[str]]): list of all clusters (clusters can have only one element)
        distance_metrics(Dict): statistics for distance matrix with similarity ratio as distance metric (mean, median, std, min, max, range)
        clustering_metrics(Dict): statistics for clustering (number of clusters, noise points, and silhouette score)
        flagged_abbreviations(List): LLM-flagged abbreviations
        list_of_dicts(List[Dict]): list of dictionaries with abbreviations matched to brick classes. defaults to COMMON_EQUIP_ABBREVIATIONS_BRICK, COMMON_POINT_ABBREVIATIONS
        parsed_count(int): total parsed across all clusters
        unparsed_count(int): total unparsed across all clusters
        total_count(int): total in all clusters

        combined_clusters:List[dict]:
        for each cluster, each Dict has
        -parser(Dict): serialized parser
        -source_code(str): parser code
        -tokens(List): emitted tokens from running parser on cluster
        -parsed_labels(List): building point labels in which parser did not contain an error
        -unparsed(List): building point labels in which parser contained an error
        -parser_metrics(Dict):
            -parsed_count(int): count of parsed for that cluster
            -unparsed_count(int): count of unparsed for that cluster
            -total_count(int): count of total for that cluster
    """

    def __init__(
        self,
        filename: str,
        col_name: str,
        num_tries=3,
        list_of_dicts=[COMMON_EQUIP_ABBREVIATIONS_BRICK, COMMON_POINT_ABBREVIATIONS],
    ):
        """
        Initializes a new SerializedParserMetrics object.

        Args:
            filename (str): file path to csv file
            col_name (str): relevant column where data is stored
            num_tries (Optional, int): max number of times for LLM to try to generate LLM_Token_Predictions object. Defaults to 3.
            list_of_dicts (Optional, List): List of dictionaries where abbreviation is matched to brick class. Defaults to [equip_abbreviations, point_abbreviations]
        """
        filename = os.path.abspath(filename)

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

        self.list_of_dicts = list_of_dicts
        self.serializers_list = []
        self.parsed_count = 0
        self.unparsed_count = 0
        self.total_count = 0
        self.combined_clusters = []

        for parser, cluster in zip(self.parsers, self.clusters):
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
                self.parsed_count += right
                self.unparsed_count += wrong
                self.total_count += right + wrong
                clustered_info["parser"] = serialized
                clustered_info["source_code"] = parser
                clustered_info["parsed_labels"] = parsed_elements
                clustered_info["tokens"] = parsed_arr
                clustered_info["unparsed_labels"] = unparsed_arr
                clustered_info["parser_metrics"] = {
                    "parsed_count": right,
                    "unparsed_count": wrong,
                    "total_count": right + wrong,
                }
                self.combined_clusters.append(clustered_info)
                self.serializers_list.append(serialized)

            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)  # remove file when complete

    def write_to_directory(self, directory: str):
        """
        Writes each parser and cluster to a file along with necessary imports.
        Saves in specified directory.

        Parameters:
        directory(str): each file containing a parser and its cluster will be saved to this directory

        Returns:
        None
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
COMBINED_ABBREVIATIONS = abbreviationsTool.make_combined_abbreviations({abbreviationsTool.make_combined_dict(self.list_of_dicts)})
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
