import pytest

from buildingmotif.label_parsing.serialized_parser_metrics import (
    ParserBuilder,
    abbreviationsTool,
)

#csv filename mapped to column name
point_parsing_columns = {"tests/unit/fixtures/point_parsing/basic_len102.csv": "BuildingNames", "tests/unit/fixtures/point_parsing/basic.csv": "BuildingNames"}

@pytest.mark.parametrize("point_label_file,point_column_name", point_parsing_columns.items())
def test_serializedParserMetrics(point_label_file, point_column_name):
    parser_builder = ParserBuilder(point_label_file, point_column_name)
    combined_and_metrics = parser_builder.combine_parsers_and_get_metrics() #emit ParserMetrics class
    if not parser_builder.distance_metrics and not parser_builder.clustering_metrics: #not enough points for multiple clusters
        assert len(parser_builder.parsers) == len(
            parser_builder.clusters
        ), "number of parsers does not match number of clusters"

        assert (
            combined_and_metrics.parsed_count + combined_and_metrics.unparsed_count
            == combined_and_metrics.total_count
        ), "number of parsed plus unparsed points do not match the total number of points"
        assert len(combined_and_metrics.combined_clusters) == len(parser_builder.parsers)
        assert(len(combined_and_metrics.serializers_list) == len(
            parser_builder.parsers
        )), "number of serialized parsers does not match number of parsers"
        for cluster_dict in combined_and_metrics.combined_clusters:
            assert (
                len(cluster_dict["tokens"]) == len(cluster_dict["parsed_labels"])
            ), "amount of parsed points do not match number of emitted tokens"
            assert (
                len(cluster_dict["unparsed_labels"]) == cluster_dict["parser_metrics"]["unparsed_count"]
            ), "amount of unparsed points do not match"
            assert (
                len(cluster_dict["parsed_labels"]) +  len(cluster_dict["unparsed_labels"])
                == cluster_dict["parser_metrics"]["total_count"]
            ), "amount of total points in the cluster does not match sum of parsed and unparsed points"
    else:
        assert len(parser_builder.parsers) == len(
            parser_builder.clusters
        ), "number of parsers does not match number of clusters"
        assert parser_builder.clustering_metrics[
            "clusters"
        ] + parser_builder.clustering_metrics["noise_points"] == len(
            parser_builder.parsers
        ), "number of parsers do not match number of clusters plus noise points"
        assert (
            parser_builder.distance_metrics["min"] >= 0
            and parser_builder.distance_metrics["max"] <= 1
        ), "distance metric min or max have gone out of range of 0-1"
        assert (
            combined_and_metrics.parsed_count + combined_and_metrics.unparsed_count
            == combined_and_metrics.total_count
        ), "number of parsed plus unparsed points do not match the total number of points"
        assert len(combined_and_metrics.combined_clusters) == len(parser_builder.parsers)
        assert(len(combined_and_metrics.serializers_list) == len(
            parser_builder.parsers
        )), "number of serialized parsers does not match number of parsers"
        for cluster_dict in combined_and_metrics.combined_clusters:
            assert (
                len(cluster_dict["tokens"]) == len(cluster_dict["parsed_labels"])
            ), "amount of parsed points do not match number of emitted tokens"
            assert (
                len(cluster_dict["unparsed_labels"]) == cluster_dict["parser_metrics"]["unparsed_count"]
            ), "amount of unparsed points do not match"
            assert (
                len(cluster_dict["parsed_labels"]) +  len(cluster_dict["unparsed_labels"])
                == cluster_dict["parser_metrics"]["total_count"]
            ), "amount of total points in the cluster does not match sum of parsed and unparsed points"