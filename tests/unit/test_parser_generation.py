from buildingmotif.label_parsing.SerializedParserMetrics import (
    SerializedParserMetrics,
    abbreviationsTool,
)
import pytest

#csv filename mapped to column name
point_parsing_columns = {"tests/unit/fixtures/point_parsing/basic_len102.csv": "BuildingNames", "tests/unit/fixtures/point_parsing/basic.csv": "BuildingNames"}

@pytest.mark.parametrize("point_label_file,point_column_name", point_parsing_columns.items())
def test_serializedParserMetrics(point_label_file, point_column_name):
    serializedParser = SerializedParserMetrics(point_label_file, point_column_name)
    if not serializedParser.distance_metrics and not serializedParser.clustering_metrics: #not enough points for multiple clusters
        assert len(serializedParser.parsers) == len(
            serializedParser.clusters
        ), "number of parsers does not match number of clusters"
        assert (
            serializedParser.parsed_count + serializedParser.unparsed_count
            == serializedParser.total_count
        ), "number of parsed plus unparsed points do not match the total number of points"
        assert len(serializedParser.combined_clusters) == len(serializedParser.parsers)
        assert(len(serializedParser.serializers_list) == len(
            serializedParser.parsers
        )), "number of serialized parsers does not match number of parsers"
        for cluster_dict in serializedParser.combined_clusters:
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
        assert len(serializedParser.parsers) == len(
            serializedParser.clusters
        ), "number of parsers does not match number of clusters"
        assert serializedParser.clustering_metrics[
            "clusters"
        ] + serializedParser.clustering_metrics["noise points"] == len(
            serializedParser.parsers
        ), "number of parsers do not match number of clusters plus noise points"
        assert (
            serializedParser.distance_metrics["min"] >= 0
            and serializedParser.distance_metrics["max"] <= 1
        ), "distance metric min or max have gone out of range of 0-1"
        assert (
            serializedParser.parsed_count + serializedParser.unparsed_count
            == serializedParser.total_count
        ), "number of parsed plus unparsed points do not match the total number of points"
        assert len(serializedParser.combined_clusters) == len(serializedParser.parsers)
        assert(len(serializedParser.serializers_list) == len(
            serializedParser.parsers
        )), "number of serialized parsers does not match number of parsers"
        for cluster_dict in serializedParser.combined_clusters:
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