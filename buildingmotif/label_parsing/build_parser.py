import random
import re
import csv

import numpy as np
from sklearn import metrics
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler

from buildingmotif.label_parsing.token_classify import classify_tokens_with_llm
from buildingmotif.label_parsing.tools import tokenizer, wordChecker, abbreviationsTool
from typing import List

MIN_CONSTANT_LENGTH = 3
scaler = MinMaxScaler()


def classify_tokens(split: List):
    """
    Classifies tokens into one of three classes: alpha (letters), numbers, or special characters. Used for
    token similarity/difference metrics.

    Parameters:
    List of tokens.

    Returns:
    List of classified tokens.
    """

    classified = []
    for group in split:
        if group.isalpha():
            classified.append("alpha")
        elif group.isdigit():
            classified.append("num")
        else:
            classified.append("special")
    return classified


def similarity_ratio_ordered(a: str, b: str):
    """
    Calculates ratio of how similar two strings are based on the ratio of the tokens they have similar (order matters) to
    the length of the longer tokenized list.

    Parameters:
    a (str): The first input string that will be tokenized.
    b (str): The second input string that will be tokenized.

    Returns:
    float: The similarity ratio between the two strings, ranging from 0.0 to 1.0.
    A ratio of 1.0 indicates identical ordered token sequences; 0.0 indicates no similarity.
    """

    classified_tokens_a = classify_tokens(tokenizer.shift_split(a))
    classified_tokens_b = classify_tokens(tokenizer.shift_split(b))

    first_unmatched = 0
    if min(len(classified_tokens_a), len(classified_tokens_b)) == len(
        classified_tokens_a
    ):
        for i in range(len(classified_tokens_a)):
            if classified_tokens_a[i] == classified_tokens_b[i]:
                first_unmatched += 1
            else:
                break
        return first_unmatched / len(classified_tokens_b)
    else:
        for i in range(len(classified_tokens_b)):
            if classified_tokens_b[i] == classified_tokens_a[i]:
                first_unmatched += 1
            else:
                break
        return first_unmatched / len(classified_tokens_a)


def get_column_data(csv_file: str, column_name: str):
    """
    Returns a list of the data inside a specified CSV column,
    in which whitespaces and new lines are removed from each entry.
    Raises exception if file cannot be found or cannot be read.

    Parameters:
    csv_file (str): file path to a csv file
    column_name (str): column name where data exists

    Returns:
    List: list of the data inside a specified CSV column,
    in which whitespaces and new lines are removed from each entry.
    """

    try:
        with open(csv_file, mode="r", newline="") as file:
            reader = csv.DictReader(file)
            if column_name not in reader.fieldnames:
                raise ValueError(
                    f"Column '{column_name}' does not exist in the CSV file."
                )

            column_contents = [
                row[column_name].replace("\n", "").replace(" ", "") for row in reader
            ]

        return column_contents

    except FileNotFoundError:
        print(f"Error: The file '{csv_file}' was not found.")
        return None

    except IOError:
        print(f"Error: Unable to read the file '{csv_file}'.")
        return None

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def make_program(user_text: str, matched_token_classes, list_of_dicts: List):
    """
    Assigns code parsers to tokens based on types and the result of applying specific parsers, resorting to
    LLM Ollama3 to seperate constants and identifiers.

    Flags unknown abbreviations with LLM Ollama3, then combines parsers assigned parsers based on the factors like
    which token they parse or if there is a sequence of similar parsers.

    Parameters:
    user_text(str): building point label
    matched_token_classes(LLM_Token_Prediction): custom class which contains each token of the string and corresponding LLM Prediction:
    Identifier, Abbreviations, Constant, or Delimiter. See token_classify.py for more details.
    list_of_dicts(List): list of dictionaries mapping an abbreviation to a brick constant.

    Returns:
    Ordered list of parsers based on the order of the original tokens.
    List of LLM-Flagged Abbreviations.
    """

    tokens = tokenizer.split_and_group(user_text, list_of_dicts)
    unparsed = tokens.copy()
    dict_predictions = {}
    flagged = []

    valid_tokens = set()
    delimiters = set()
    combined_abbreviations = abbreviationsTool.make_combined_abbreviations(
        list_of_dicts
    )# combines dictionaries, sorts keys by decreasing length, and makes combined dictionary an abbreviations object

    for token in tokens:
        if not token.isalnum():
            delimiters.add(token)
        elif (
            wordChecker.check_word_validity(token) and len(token) >= MIN_CONSTANT_LENGTH
        ):
            valid_tokens.add(token)
        else:
            if combined_abbreviations(token) and not any(
                r.error for r in combined_abbreviations(token)
            ):
                dict_predictions[token] = "COMBINED_ABBREVIATIONS"

    # Assign classifications
    for token in delimiters:
        dict_predictions[token] = "delimiters"
    for token in valid_tokens:
        dict_predictions[token] = f'regex(r"[a-zA-Z]{{1,{len(token)}}}", Constant)'

    unparsed = [
        token
        for token in tokens
        if token not in delimiters
        and token not in valid_tokens
        and token not in dict_predictions.keys()
    ]  # remove already parsed tokens

    # make dictionary for LLM_Token_Predictions where the key is the token and value is the classification
    class_token_dict = {
        ct.token: ct.classification for ct in matched_token_classes.predictions
    }

    for token in unparsed:
        classification = class_token_dict.get(token)
        if classification:
            if classification == "Abbreviations":
                flagged.append(
                    token
                )  # append all tokens the llm predicts as an Abbreviations to the flagged list
        if (
            wordChecker.check_word_validity(token) and len(token) >= MIN_CONSTANT_LENGTH
        ) or classification == "Constant":  # check if a token is constant by using a word checker library or with llm prediction
            dict_predictions[token] = f'regex(r"[a-zA-Z]{{1,{len(token)}}}", Constant)'
        else:
            dict_predictions[token] = (
                f'regex(r"[a-zA-Z0-9]{{1,{len(token)}}}", Identifier)'
            )

    arr = [dict_predictions.get(token) for token in tokens]
    # add all parsers to a list based on the original token order
    final_groups = []
    left = 0
    right = 1
    arr_size = len(arr)

    # use two pointers to walk through parser list and combine them with parser classes like until, many, and rest
    while right < arr_size:
        if (
            arr[left] == "COMBINED_ABBREVIATIONS"
            and arr[right] == "COMBINED_ABBREVIATIONS"
        ):  # two abbreviations in sequence
            final_groups.append("many(" + arr[left] + ")")
            left += 2
            right = left + 1
        elif (
            "Identifier" in arr[left]
            and "Constant" not in arr[right]
            and "Identifier" not in arr[right]
        ):  # identifier before an abbreviation or delimiter
            final_groups.append(f"until({arr[right]}, Identifier)")
            final_groups.append(arr[right])
            left += 2
            right = left + 1
        elif (
            "Constant" in arr[left]
            and "Constant" not in arr[right]
            and "Identifier" not in arr[right]
        ):  # constant before an abbreviation or delimiter
            final_groups.append(f"until({arr[right]}, Constant)")
            final_groups.append(arr[right])
            left += 2
            right = left + 1
        elif (
            "Identifier" in arr[left] and "Identifier" in arr[right]
        ):  # two identifiers in sequence
            if (
                right + 1 == arr_size - 1 and "Identifier" in arr[right + 1]
            ) or right == arr_size - 1:  # last two or three elements are all identifiers
                final_groups.append("identifier")
                left = len(arr)
                break
            elif (
                right + 1 == arr_size - 2
                and "Identifier" not in arr[right + 1]
                and "Constant" not in arr[right + 1]
            ):
                # two elements are identifiers, third element is either a delimiter or abbrev
                final_groups.append(f"until({arr[right + 1]}, Identifier)")
                left = right + 1
            else:
                # Calculate the maximum lengths of first_regex and second_regex
                max_length_first = int(re.search(r"\{1,(\d+)\}", arr[left]).group(1))
                max_length_second = int(re.search(r"\{1,(\d+)\}", arr[right]).group(1))
                combined_length = max_length_first + max_length_second

                combined_regex = r"[a-zA-Z0-9]{1,%d}" % combined_length
                combined_regex = str(combined_regex)

                combined = f'regex(r"{combined_regex}", Identifier)'
                final_groups.append(combined)
                left += 2
                right = left + 1
        elif (
            "Constant" in arr[left] and "Constant" in arr[right]
        ):  # two constants in sequence
            if (
                right + 1 == arr_size - 1 and "Constant" in arr[right + 1]
            ) or right == arr_size - 1:  # last two or three elements are all constants
                final_groups.append('regex(r"[a-zA-Z]+", Constant)')
                left = len(arr)
                break
            elif (
                right + 1 == arr_size - 2
                and "Identifier" not in arr[right + 1]
                and "Constant" not in arr[right + 1]
            ):
                final_groups.append(
                    f"until({arr[right + 1]}, Constant)"
                )  # two elements are constanrs, third element is either a delimiter or abbrev
                left = right + 1
            else:
                max_length_first = int(re.search(r"\{1,(\d+)\}", arr[left]).group(1))
                max_length_second = int(re.search(r"\{1,(\d+)\}", arr[right]).group(1))
                combined_length = max_length_first + max_length_second

                combined_regex = r"[a-zA-Z]{1,%d}" % combined_length
                combined_regex = str(combined_regex)

                combined = f'regex(r"{combined_regex}", Constant)'
                final_groups.append(combined)
                left += 2
                right = left + 1
        else:
            final_groups.append(arr[left])
            left += 1
            right = left + 1
    if left < len(arr):
        final_groups.append(
            arr[left]
        )  # append last element if left pointer is not at end

    if "Constant" in final_groups[len(final_groups) - 1]:  # last element is a constant
        final_groups.pop(len(final_groups) - 1)
        final_groups.append('regex(r"[a-zA-Z]+", Constant)')
    elif (
        "Identifier"
        in final_groups[len(final_groups) - 1]  # last element is an identifier
    ):  # last element is an identifier
        final_groups.pop(len(final_groups) - 1)
        final_groups.append("identifier")
    return final_groups, flagged


def group_by_clusters(filename: str, col_name: str):
    """
    Uses DBScan clustering to group list of names returned from CSV file column.

    Parameters:
    filename(str): file path to csv file
    col_name(str): column name

    Returns:
    List of lists of clustered building points.
    List of lists of noise points.
    """

    noise = []
    clusters = []
    distance_matrix_metrics = {}
    clustering_metrics = {}

    if get_column_data(filename, col_name) is not None:
        data_list = get_column_data(filename, col_name)

    n = len(data_list)
    distance_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            dist = similarity_ratio_ordered(data_list[i], data_list[j])
            distance_matrix[i, j] = dist
            distance_matrix[j, i] = dist

    distance_matrix_metrics = {
        "mean": np.mean(distance_matrix),
        "median": np.median(distance_matrix),
        "std": np.std(distance_matrix),
        "min": np.min(distance_matrix),
        "max": np.max(distance_matrix),
        "range": np.max(distance_matrix) - np.min(distance_matrix),
    }

    scaled_distance_matrix = scaler.fit_transform(distance_matrix)
    neigh = NearestNeighbors(n_neighbors=4, metric="precomputed")
    nbrs = neigh.fit(scaled_distance_matrix)
    distances, indices = nbrs.kneighbors(scaled_distance_matrix)
    distances = np.sort(distances[:, 1])

    dbscan = DBSCAN(eps=0.125, min_samples=4).fit(scaled_distance_matrix)
    labels = dbscan.fit_predict(scaled_distance_matrix)

    # Number of clusters in labels, ignoring noise if present.
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise_ = list(labels).count(-1)
    clustering_metrics = {
        "clusters": n_clusters_,
        "noise points": n_noise_,
        "clustering_score": metrics.silhouette_score(scaled_distance_matrix, labels),
    }

    for cluster_id in np.unique(labels):
        cluster_strings = [data_list[i] for i in np.where(labels == cluster_id)[0]]
        if cluster_id == -1:
            noise.append(cluster_strings)
        else:
            clusters.append(cluster_strings)
        # print(f"Cluster {cluster_id}: {cluster_strings}")
    return clusters, noise, distance_matrix_metrics, clustering_metrics


def generate_parsers_for_points(
    filename: str, col_name: str, num_tries: int, list_of_dicts: List
):
    """
    Generates parsers for every building point label from the CSV file column because
    DBScan was unable to create more than one cluster.

    Parameters:
    filename(str): file path to csv file
    col_name(str): column name
    num_tries(int): number of times for LLM to attempt to generate token predictions (LLM_Token_Predictions)
    list_of_dicts(List): list of dictionaries to be used for abbreviations that map to brick classes

    Returns:
    List of list of parsers.
    List of list of each point.
    List of all flagged abbreviations.

    """

    parsers = []
    clusters = []
    flagged = []
    if get_column_data(filename, col_name) is not None:
        data_list = get_column_data(filename, col_name)
        for data in data_list:
            try:
                llm_output = classify_tokens_with_llm(data, list_of_dicts, num_tries)
            except Exception as e:
                print(e)
                print(f"num_tries exceeded {num_tries}")
                continue
            program_arr, flagged = make_program(data, llm_output, list_of_dicts)
            random_generated_parser = (
                "parser_noise_"
                + str(len(program_arr))
                + "_"
                + str(random.randint(1, 1000))
            )
            parser = (
                random_generated_parser + " = sequence(" + ", ".join(program_arr) + ")"
            )
            parsers.append(parser)
            clusters.append([data])
    return parsers, clusters, flagged


def generate_parsers_for_clusters(
    filename: str, col_name: str, num_tries: int, list_of_dicts: List
):
    """
    Generates parsers for every cluster from the list of building point labels from CSV file column

    Parameters:
    filename(str): file path to csv file
    col_name(str): column name
    num_tries(int): number of times for LLM to attempt to generate token predictions (LLM_Token_Predictions)
    list_of_dicts(List): list of dictionaries to be used for abbreviations that map to brick classes

    Returns:
    List of list of parsers.
    List of list of each cluster with building point labels.
    Dictionary of distance metrics with distance being the similarity ratio metric, like: mean, median, mode, std, min, max, range.
    Dictionary of clustering metrics like number of clusters, number of noise points, silhouette score.
    List of all flagged abbreviations.
    """

    map_parser_to_cluster = {}
    clusters, noise, distance_metrics, cluster_metrics = group_by_clusters(
        filename, col_name
    )
    flagged = []

    for arr_of_point_names in clusters:
        point_name = arr_of_point_names[random.randint(0, len(arr_of_point_names) - 1)]
        try:
            llm_output = classify_tokens_with_llm(point_name, list_of_dicts, num_tries)
        except Exception as e:
            print(e)
            print(f"num_tries exceeded {num_tries}")
            continue
        program_arr, flagged = make_program(point_name, llm_output, list_of_dicts)
        random_generated_parser = (
            "parser_lencluster_"
            + str(len(program_arr))
            + "_"
            + str(random.randint(1, 1000))
        )
        parser = random_generated_parser + " = sequence(" + ", ".join(program_arr) + ")"
        map_parser_to_cluster[parser] = arr_of_point_names

    for noise_point in noise[0]:
        try:
            llm_output = classify_tokens_with_llm(noise_point, list_of_dicts, num_tries)
        except Exception as e:
            print(e)
            print(f"num_tries exceeded {num_tries}")
            continue
        program_arr, flagged = make_program(noise_point, llm_output, list_of_dicts)
        random_generated_parser = (
            "parser_noise_" + str(len(program_arr)) + "_" + str(random.randint(1, 1000))
        )
        parser = random_generated_parser + " = sequence(" + ", ".join(program_arr) + ")"
        map_parser_to_cluster[parser] = [noise_point]

    return (
        map_parser_to_cluster.keys(),
        map_parser_to_cluster.values(),
        distance_metrics,
        cluster_metrics,
        flagged,
    )
