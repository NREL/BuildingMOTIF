import importlib.util
import os
import re
from build_parser import generate_parsers_for_clusters, generate_parsers_for_points
from combinators import COMMON_EQUIP_ABBREVIATIONS_BRICK, COMMON_POINT_ABBREVIATIONS, make_combined_abbreviations

# tests for code
# write function documentation, return types and params, also add comment on temp file, why?


class Combined_Parsers:

    def __init__(
        self,
        filename: str,
        col_name: str,
        num_tries=3,
        list_of_dicts=[COMMON_EQUIP_ABBREVIATIONS_BRICK, COMMON_POINT_ABBREVIATIONS],
    ):
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
        except ValueError as e:
            self.parsers, self.clusters, self.flagged_abbreviations = (
                generate_parsers_for_points(
                    filename, col_name, num_tries, list_of_dicts
                )
            )
            self.distance_metrics, self.clustering_metrics = {}, {}

        self.list_of_dicts = list_of_dicts
        self.parsed_count = 0
        self.unparsed_count = 0
        self.total_count = 0
        self.combined_clusters = []

        for parser, cluster in zip(self.parsers, self.clusters):
            clustered_info = {}
            try:
                temp_filename = os.path.join(os.getcwd(), "temp_parser.py")

                with open(temp_filename, mode="w") as temp_file:
                    pattern = re.compile(r"([^\s]+)")
                    parser_var = pattern.match(parser)[0]
                    temp_file.write(
                        f"""
from buildingmotif.label_parsing.combinators import *
from buildingmotif.label_parsing.parser import parser_on_list
import rdflib
                        """
                    )
                    temp_file.write(f"""
COMBINED_ABBREVIATIONS = make_combined_abbreviations({list_of_dicts})
                    """
                    )
                    temp_file.write(
                        f"""
{parser}"""
                    )
                    temp_file.write(
                        f"""
cluster = {cluster}"""
                    )
                    temp_file.write(
                        f"""
def run_parser():
    parsed, unparsed, right, wrong = parser_on_list({parser_var}, cluster)
    return parsed, unparsed, right, wrong"""
                    )

                # Load the module from the temporary file
                spec = importlib.util.spec_from_file_location(
                    "generated", temp_filename
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Call the function defined in the module
                parsed_arr, unparsed_arr, right, wrong = module.run_parser()
                self.parsed_count += right
                self.unparsed_count += wrong
                self.total_count += right + wrong
                clustered_info["parser"] = module
                clustered_info["source_code"] = parser
                clustered_info["tokens"] = parsed_arr
                clustered_info["unparsed"] = unparsed_arr
                clustered_info["parser_metrics"] = {
                    "parsed_count": right,
                    "unparsed_count": wrong,
                    "total_count": right + wrong,
                }
                self.combined_clusters.append(clustered_info)

            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

    def write_to_directory(self, directory: str):
        if not os.path.exists(directory):
            os.makedirs(directory)

        for parser, cluster in zip(self.parsers, self.clusters):
            pattern = re.compile(r"([^\s]+)")
            parser_var = pattern.match(parser)[0]
            filename = parser_var + ".py"
            with open(os.path.join(directory, filename), "w") as file:
                file.write(
                    f"""
from buildingmotif.label_parsing.combinators import *
from buildingmotif.label_parsing.parser import parser_on_list
import rdflib
                    """
                )
                file.write(f"""
COMBINED_ABBREVIATIONS = make_combined_abbreviations({self.list_of_dicts})
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


combined = Combined_Parsers("docs/basic_len102.csv", "BuildingNames")
#combined = Combined_Parsers("docs/basic.csv", "BuildingNames")

combined.write_to_directory("generated")
print("all parsers: ", combined.parsers)
print("all clusters: ", combined.clusters)
print("potential abbreviations: ", combined.flagged_abbreviations)

print("distances info: ")
for k, v in combined.distance_metrics.items():
    print(k, v)

print("clustering info: ")
for k, v in combined.clustering_metrics.items():
    print(k, v)

print("total parsed for all clusters: ", combined.parsed_count)
print("total unparsed for all clusters: ", combined.unparsed_count)
print("total for all clusters: ", combined.total_count)

print("combined clustering information for each cluster: ")
for i in combined.combined_clusters:
    for k,v in i.items():
        print(k,v)