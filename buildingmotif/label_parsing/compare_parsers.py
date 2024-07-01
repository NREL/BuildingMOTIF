import nltk


def edit_distance_tokenizer(res):
    """
    Used to add tokens from parsers into a list
    """

    arr_tokens = []
    for r in res:
        value_token = (r.value, r.token)
        arr_tokens.append(value_token)
    return arr_tokens


def jaccard_distance_tokenizer(res):
    """
    Used to add tokens from parsers into a set
    """

    set_tokens = set()
    for r in res:
        t = (r.value, r.token)
        set_tokens.add(t)
    return set_tokens


def find_parsers_diff(ground_parser, test_parser, input_file):
    """
    Finds the edit distance and jaccard distance between the resulting tokens
    from two different parsers, as well as the union and difference between the tokens.
    """

    with open(input_file, "r") as filename:
        list_names = [line.strip() for line in filename.readlines()]

    ed_arr = []
    j_arr = []

    for point in list_names:

        pre = ground_parser(point)
        post = test_parser(point)

        ground_ed = edit_distance_tokenizer(pre)
        ground_j = jaccard_distance_tokenizer(pre)

        val_j = jaccard_distance_tokenizer(post)
        val_ed = edit_distance_tokenizer(post)

        ed = nltk.edit_distance(val_ed, ground_ed)
        jdist = nltk.jaccard_distance(val_j, ground_j)
        ed_arr.append(ed)
        j_arr.append(jdist)

        print("input: ", point)
        print("\n")
        union = val_j.union(ground_j)
        print("union ", union)
        print("\n")
        unique_ground = ground_j - val_j
        print("unique to ground ", unique_ground)
        print("\n")
        unique_gen = val_j - ground_j
        print("unique to gen ", unique_gen)
        print("\n")

    print(f"{'Input Name':<30} {'Edit Distance':<15} {'Jaccard Distance':<15}")
    print("-" * 70)

    # Print data aligned in columns
    for i in range(len(list_names)):
        print(f"{list_names[i]:<30} {ed_arr[i]:<15.4f} {j_arr[i]:<15.4f}")

    # return list_names, ed_arr, j_arr
