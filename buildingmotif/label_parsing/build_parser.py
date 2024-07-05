import os
import random
import re
import sys
import csv

import numpy as np
from sklearn import metrics
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler
#import matplotlib.pyplot as plt

from buildingmotif.label_parsing.combinators import (
    equip_abbreviations,
    point_abbreviations,
    make_abbreviations_list,
    make_combined_abbreviations
)
from buildingmotif.label_parsing.token_classify import classify_tokens_with_llm
from buildingmotif.label_parsing.tools import codeLinter, tokenizer, wordChecker

MIN_CONSTANT_LENGTH = 3
SAVE_DIR = "generated"
scaler = MinMaxScaler()


def classify_tokens(split: list):
    # Classify tokens based on type
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
    # calculates ratio of how similar two strings are (order matters of tokens) over the length of the longer string
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

def get_column_data(csv_file, column_name):
    try:
        with open(csv_file, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            if column_name not in reader.fieldnames:
                raise ValueError(f"Column '{column_name}' does not exist in the CSV file.")
            
            column_contents = [row[column_name].replace('\n', '').replace(' ', '') for row in reader]
            
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

def generate_parsers_for_points(filename: str, col_name: str, num_tries: int, list_of_dicts):
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
                "parser_noise_" + str(len(program_arr)) + "_" + str(random.randint(1, 1000))
            )
            parser = random_generated_parser + " = sequence(" + ", ".join(program_arr) + ")"
            parsers.append(parser)
            clusters.append([data])
    return parsers, clusters, flagged



def group_by_clusters(filename: str, col_name: str):
    # groups using DBScan clustering, then returns list of all clusters and list of noise points with clustering metrics
    noise = []
    clusters = []
    distance_matrix_metrics = {}
    clustering_metrics = {}

    # with open(filename, "r") as file:
    #     data_list = [
    #         line.replace(" ", "").replace("\n", "") for line in file.readlines()
    #     ]
    if get_column_data(filename, col_name) is not None:
        data_list = get_column_data(filename, col_name)

    n = len(data_list)
    distance_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            dist = similarity_ratio_ordered(data_list[i], data_list[j])
            distance_matrix[i, j] = dist
            distance_matrix[j, i] = dist

    
    distance_matrix_metrics = {"mean":np.mean(distance_matrix), "median":np.median(distance_matrix), 
    "std":np.std(distance_matrix), "min":np.min(distance_matrix), "max":np.max(distance_matrix), 
    "range":np.max(distance_matrix) - np.min(distance_matrix)}

    scaled_distance_matrix = scaler.fit_transform(distance_matrix)
    neigh = NearestNeighbors(n_neighbors=4, metric="precomputed")
    nbrs = neigh.fit(scaled_distance_matrix)
    distances, indices = nbrs.kneighbors(scaled_distance_matrix)
    distances = np.sort(distances[:, 1])

    dbscan = DBSCAN(eps=0.125, min_samples=4).fit(scaled_distance_matrix) 
    labels = dbscan.fit_predict(scaled_distance_matrix)

    '''
    unique_labels = set(labels)
    core_samples_mask = np.zeros_like(labels, dtype=bool)
    core_samples_mask[dbscan.core_sample_indices_] = True

    colors = [plt.cm.Spectral(each) for each in np.linspace(0, 1, len(unique_labels))]
    for k, col in zip(unique_labels, colors):
        if k == -1:
            # Black used for noise.
            col = [0, 0, 0, 1]

        class_member_mask = labels == k

        xy = scaled_distance_matrix[class_member_mask & core_samples_mask]
        plt.plot(
            xy[:, 0],
            xy[:, 1],
            "o",
            markerfacecolor=tuple(col),
            markeredgecolor="k",
            markersize=14,
        )

        xy = scaled_distance_matrix[class_member_mask & ~core_samples_mask]
        plt.plot(
            xy[:, 0],
            xy[:, 1],
            "o",
            markerfacecolor=tuple(col),
            markeredgecolor="k",
            markersize=6,
        )
    plt.show()
    '''

    # Number of clusters in labels, ignoring noise if present.
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise_ = list(labels).count(-1)
    clustering_metrics= {"clusters":n_clusters_, 
    "noise points":n_noise_, 
    "clustering_score":metrics.silhouette_score(scaled_distance_matrix, labels)}

    for cluster_id in np.unique(labels):
        cluster_strings = [data_list[i] for i in np.where(labels == cluster_id)[0]]
        if cluster_id == -1:
            noise.append(cluster_strings)
        else:
            clusters.append(cluster_strings)
        # print(f"Cluster {cluster_id}: {cluster_strings}")
    return clusters, noise, distance_matrix_metrics, clustering_metrics


def make_program(user_text:str, matched_token_classes, list_of_dicts):
    """
    Assigns parsers to tokens based on types and the result of applying specific parsers, resorting to
    LLM to seperate constants and identifiers.
    Flags unknown abbreviations, then combines parsers assigned parsers based on the factors like
    which token they parse or if there is a sequence of similar parsers.
    Returns an ordered list of parsers.
    """
    tokens = tokenizer.split_and_group(user_text, list_of_dicts)
    #print(tokens)
    unparsed = tokens.copy()
    dict_predictions = {}
    flagged = []

    valid_tokens = set()
    delimiters = set()
    combined_abbreviations = make_combined_abbreviations(list_of_dicts)
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
                break
        

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
    ]

    # Optimized secondary classification using a dictionary
    class_token_dict = {
        ct.token: ct.classification for ct in matched_token_classes.predictions
    }
    # print(class_token_dict)
    for token in unparsed:
        classification = class_token_dict.get(token)
        if classification:
            if classification == "Abbreviations":
                flagged.append(token)
        if (
            wordChecker.check_word_validity(token) and len(token) >= MIN_CONSTANT_LENGTH
        ) or classification == "Constant":
            dict_predictions[token] = f'regex(r"[a-zA-Z]{{1,{len(token)}}}", Constant)'
        else:
            dict_predictions[
                token
            ] = f'regex(r"[a-zA-Z0-9]{{1,{len(token)}}}", Identifier)'

    arr = [dict_predictions.get(token) for token in tokens]
    final_groups = []
    left = 0
    right = 1
    arr_size = len(arr)

    while right < arr_size:
        if (
            arr[left] == "COMBINED_ABBREVIATIONS" and arr[right] == "COMBINED_ABBREVIATIONS"
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
        final_groups.append(arr[left])

    if "Constant" in final_groups[len(final_groups) - 1]:  # last element is a constant
        final_groups.pop(len(final_groups) - 1)
        final_groups.append('regex(r"[a-zA-Z]+", Constant)')
    elif (
        "Identifier" in final_groups[len(final_groups) - 1]
    ):  # last element is an identifier
        final_groups.pop(len(final_groups) - 1)
        final_groups.append("identifier")
    return final_groups, flagged


def generate_parsers_for_clusters(filename: str, col_name:str, num_tries: int, list_of_dicts):
    '''
    Generate parsers for each cluster and 
    returns a map of parser to cluster as well as 
    generating parser for each point in noise
    '''
    map_parser_to_cluster = {}
    clusters, noise, distance_metrics, cluster_metrics = group_by_clusters(filename, col_name)
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

    return map_parser_to_cluster.keys(), map_parser_to_cluster.values(), distance_metrics, cluster_metrics, flagged


def generate_program(point_name, program_arr, file_to_write, test_file, mode):
    """
    Writes ordered, combined parsers based on mode to either a file 
    or a directory with files to test clusters.
    """

    prog = f"parser_for{len(program_arr)}"
    if mode == "combined":
        # each parser for each token length will be written to same file, to prevent collisions
        prog = f"parser_for{len(program_arr)}_{random.randint(1, 1000)}"

    parser = f"{prog} = sequence("
    parser += ", ".join(program_arr)
    parser += ")\n"
    path = SAVE_DIR + "/" + f"{file_to_write}"

    if mode == "separate":
        with open(path, "w") as output:
            output.write(
                """
from buildingmotif.label_parsing.combinators import *
from buildingmotif.label_parsing.parser import *
            """
            )
            output.write(
                f"""
{parser}
"""
            )
            output.write(
                f"""
    \n
parsed, unparsed, right, wrong = parser_on_list({prog},"{test_file}")
print("right: ", right)
print("right percentage: ", right / (right + wrong))
print("wrong: ", wrong)
print("wrong percentage: ", wrong / (right + wrong))
print("total: ", right + wrong)
print(unparsed)
print({prog}(\"{point_name}\"))
# for elem in unparsed:
#     print({prog}(elem))
    """
            )
        codeLinter._run(f"{os.path.join(SAVE_DIR, file_to_write)}")
    else:
        return parser


def parse_file(input_file, mode, list_of_dicts):
    """
    Driver program that applies parser generation algorithm to a file, clusters the contents with DBScan,
    will either write it as a sequence of parsers combined into one parser
    or multiple different parsers in different files for debugging purposes.
    Writes all noise to one file, no parser generated.
    """

    if not os.path.exists(SAVE_DIR) and mode == "separate":
        os.makedirs(SAVE_DIR)

    list_parsers = []
    all_parsers = """
final_parser = choice_for_list(
"""

    metrics = f"""
parsed, unparsed, right, wrong =final_parser("{input_file}")
print("right: ", right)
print("right percentage: ", right / (right+wrong))
print("wrong: ", wrong)
print("wrong percentage: ", (wrong) / (right+wrong))
print("total: ", right+wrong)
#print(unparsed)
"""
    clusters, noise, distance_metrics, cluster_metrics = group_by_clusters(input_file, col_name)
    for arr_of_point_names in clusters:
        point_name = arr_of_point_names[random.randint(0, len(arr_of_point_names) - 1)]
        len_token = len(tokenizer.split_and_group(point_name))
        try:
            llm_output = classify_tokens_with_llm(point_name, list_of_dicts, num_tries)
        except Exception as e:
            print(e)
            print(f"num_tries exceeded {num_tries}")
            continue
        program_arr, flagged = make_program(point_name, llm_output, list_of_dicts=[equip_abbreviations, point_abbreviations])
        rand_num = random.randint(1, 1000)
        test_file = f"test_{len_token}_{rand_num}.txt"
        file_to_write = f"program_for_length_{len_token}_{rand_num}.py"
        if mode == "separate":
            with open(os.path.join(SAVE_DIR, test_file), "w") as test:
                test.write(("\n".join(arr_of_point_names)))
            generate_program(
                point_name,
                program_arr,
                file_to_write,
                test_file,
                "separate",
            )
        else:
            list_parsers.append(
                generate_program(
                    point_name,
                    program_arr,
                    file_to_write,
                    input_file,
                    "combined",
                )
            )

    if len(noise[0]) > 0 and mode == "separate":
        with open(os.path.join(SAVE_DIR, "noise.txt"), "w") as test:
            test.write(("\n".join(noise[0])))

    pattern = re.compile(r"parser_for\d+_\d+")
    file_to_write = "combined.py"
    if mode == "combined":
        with open(file_to_write, "w") as output:
            matched_parsers = [
                match.group() for s in list_parsers for match in pattern.finditer(s)
            ]
            all_parsers += ", ".join(matched_parsers)
            all_parsers += ")\n"
            all_parsers += metrics
            output.write(
                """
from buildingmotif.label_parsing.combinators import *
from buildingmotif.label_parsing.parser import *
    """
            )
            for parser in list_parsers:
                output.write(
                    f"""
{parser}"""
                )
            output.write(all_parsers)
        codeLinter._run(f"{file_to_write}")


# command line arguements are filename and mode ["separate", "combined", "terminal"]
arg_len = len(sys.argv)
if arg_len != 3:
    print(
        "Must specify file path to test file or Must specify file saving method, either combined or separate"
    )
elif not isinstance(sys.argv[1], str):
    print("filename must be string")
elif sys.argv[2] not in ["separate", "combined", "terminal"]:
    print(
        "Must specify file saving method, combined, or separate, or just terminal output"
    )
else:
    file = sys.argv[1]
    mode = sys.argv[2]
    try:
        if mode != "terminal":
            parse_file(file, mode)
        else:
            for k, v in generate_parsers_for_clusters(file).items():
                print(k)
                print(v)
                print("\n")
    except FileNotFoundError:
        print("File not found:", file)
    except Exception as e:
        print("Error opening file:", e)