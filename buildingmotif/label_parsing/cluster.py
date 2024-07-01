import random

import matplotlib.pyplot as plt
import nltk
import numpy as np
from build_parser import make_program
from sklearn import metrics
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler
from token_classify import classify_tokens_with_llm
from tools import tokenizer


def classify_tokens(split: list):
    # Classify tokens based on type
    classified = []
    for group in split:
        if group.isalpha():
            classified.append("alpha")
        elif group.isdigit():
            classified.append("num")
        # elif group == " ":
        #     classified.append("space")
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


def count_occurrences(a):
    # count occurence of each token and returns a map of count to token
    element_count = {}

    for elem in a:
        if elem in element_count:
            element_count[elem] += 1
        else:
            element_count[elem] = 1
    result_map = {elem: element_count[elem] for elem in set(a)}

    return result_map.values()


def q_gram_distance(a: str, b: str):
    # adds count of each token for each string and finds the difference-q gram
    classified_tokens_a = classify_tokens(tokenizer.shift_split(a))
    classified_tokens_b = classify_tokens(tokenizer.shift_split(b))
    return abs(
        sum(count_occurrences(classified_tokens_a))
        - sum(count_occurrences(classified_tokens_b))
    )


def edit_distance(a: str, b: str):
    # finds edit distance between token sets
    classified_tokens_a = classify_tokens(tokenizer.shift_split(a))
    classified_tokens_b = classify_tokens(tokenizer.shift_split(b))
    ed = nltk.edit_distance(classified_tokens_a, classified_tokens_b)
    return ed


scaler = MinMaxScaler()


def group_by_clusters(filename: str):
    # groups using DBScan clustering, then returns list of all clusters and list of noise with clustering metrics
    noise = []
    clusters = []
    with open(filename, "r") as file:
        data_list = [
            line.replace(" ", "").replace("\n", "") for line in file.readlines()
        ]

    n = len(data_list)
    distance_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            dist = similarity_ratio_ordered(data_list[i], data_list[j])
            distance_matrix[i, j] = dist
            distance_matrix[j, i] = dist

    print("distance matrix: ")
    print("mean ", np.mean(distance_matrix))
    print("median ", np.median(distance_matrix))
    print("std ", np.std(distance_matrix))
    print("min ", np.min(distance_matrix))
    print("max ", np.max(distance_matrix))
    print("range ", np.max(distance_matrix) - np.min(distance_matrix))
    print("\n")

    scaled_distance_matrix = scaler.fit_transform(distance_matrix)
    neigh = NearestNeighbors(n_neighbors=4, metric="precomputed")
    nbrs = neigh.fit(scaled_distance_matrix)
    distances, indices = nbrs.kneighbors(scaled_distance_matrix)
    distances = np.sort(distances[:, 1])

    dbscan = DBSCAN(eps=0.125, min_samples=4).fit(scaled_distance_matrix)  # 0.4
    labels = dbscan.fit_predict(scaled_distance_matrix)

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

    # Number of clusters in labels, ignoring noise if present.
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise_ = list(labels).count(-1)

    print("clustering information: ")
    print("Estimated number of clusters: %d" % n_clusters_)
    print("Estimated number of noise points: %d" % n_noise_)
    print(
        f"Silhouette Coefficient: {metrics.silhouette_score(scaled_distance_matrix, labels):.3f}\n"
    )

    for cluster_id in np.unique(labels):
        cluster_strings = [data_list[i] for i in np.where(labels == cluster_id)[0]]
        if cluster_id == -1:
            noise.append(cluster_strings)
        else:
            clusters.append(cluster_strings)
        # print(f"Cluster {cluster_id}: {cluster_strings}")
    return clusters, noise


def generate_parsers_for_clusters(filename: str):
    # generate parsers for each cluster and returns a map of parser to cluster as well as generating parser for each point in noise
    map_parser_to_cluster = {}
    clusters, noise = group_by_clusters(filename)

    for arr_of_point_names in clusters:
        point_name = arr_of_point_names[random.randint(0, len(arr_of_point_names) - 1)]
        try:
            llm_output = classify_tokens_with_llm(point_name)
        except Exception as e:
            print(e)
            continue
        program_arr = make_program(point_name, llm_output)
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
            llm_output = classify_tokens_with_llm(noise_point)
        except Exception as e:
            print(e)
            continue
        program_arr = make_program(noise_point, llm_output)
        random_generated_parser = (
            "parser_noise_" + str(len(program_arr)) + "_" + str(random.randint(1, 1000))
        )
        parser = random_generated_parser + " = sequence(" + ", ".join(program_arr) + ")"
        map_parser_to_cluster[parser] = noise_point

    return map_parser_to_cluster


"""
#specify filename
for k,v in generate_parsers_for_clusters("docs/basic_len102.txt").items():
    print(k)
    print(v)
    print("\n")
"""
