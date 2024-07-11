import subprocess
from typing import List

import enchant

from buildingmotif.label_parsing.combinators import abbreviations


class Lint_Code:
    """
    Runs black in a subprocess to lint code
    """

    def _run(self, filepath: str):
        """
        Lints a file with black.
        """
        subprocess.run(
            f"black {filepath}",
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            timeout=3,
            check=False,
        )


class Abbreviations_Tools:
    """
    Process dictionaries or list of dictionaries by making keys uppercase, sorting by key length, and making
    abbreviation parser objects.
    """

    def make_abbreviations(self, input_dict):
        """
        Sorts and makes all keys uppercase in a dictionary.

        :param input_dict: Input dictionary.
        :type input_dict: dict

        :return: Abbreviation parser obtained from the processed dictionary.
        :rtype: abbreviation parser
        """

        sorted_points = sorted(
            list(input_dict.items()), key=lambda key: len(key[0]), reverse=True
        )
        processed = {ele[0].upper(): ele[1] for ele in sorted_points}
        return abbreviations(processed)

    def make_combined_abbreviations(self, list_of_dicts):
        """
        Combines into one dictionary.
        Sorts and makes all keys uppercase for that dictionary and makes abbreviations parser.

        :param list_of_dicts: List of dictionaries.
        :type list_of_dicts: List[dict]

        :return: Abbreviation parser obtained from the processed list of dictionaries.
        :rtype: abbreviation parser

        """

        combined = {}
        for d in list_of_dicts:
            combined.update(d)
        sorted_points = sorted(
            list(combined.items()), key=lambda key: len(key[0]), reverse=True
        )
        processed = {ele[0].upper(): ele[1] for ele in sorted_points}
        return abbreviations(processed)

    def make_combined_dict(self, list_of_dicts):
        """
        Combines into one dictionary.
        Sorts and makes all keys uppercase for that dictionary.

        :param list_of_dicts: List of dictionaries to process and combine.
        :type list_of_dicts: List[dict]

        :return: Processed and combined dictionary.
        :rtype: dict
        """

        combined = {}
        for d in list_of_dicts:
            combined.update(d)
        sorted_points = sorted(
            list(combined.items()), key=lambda key: len(key[0]), reverse=True
        )
        processed = {ele[0].upper(): ele[1] for ele in sorted_points}
        return processed


abbreviationsTool = Abbreviations_Tools()


class Check_Valid_Word:
    """
    Checks word validity using enchant package, used for one way of detecting constants
    """

    def check_word_validity(self, input_str: str):
        """
        Checks word validity using enchant package.

       :param input_str: Input string to check.
       :type input_str: str

       :return: Boolean indicating whether the input string is valid and only made of letters.
       :rtype: bool
        """

        d = enchant.Dict("en_US")
        if d.check(input_str) and input_str.isalpha():
            return True
        else:
            return False


wordChecker = Check_Valid_Word()  # instantiates word checker for use by tokenizer class


class Tokenizer:
    """
    Tokenizes a word based on alphanumeric or special character shifts
    """

    def shift_split(self, word: str):
        """
        Tokenizes a word based on alphanumeric or special character shifts.

        :param word: Input string to separate into tokens.
        :type word: str

        :return: List of separated tokens.
        :rtype: List[str]
        """

        word = word.replace(" ", "")
        left = 0
        right = len(word) - 1
        tokened = []
        while left <= right:
            curr_char = word[left]
            curr_is_alpha = curr_char.isalpha()
            curr_is_special = curr_char.isalnum()

            start_index = left
            left += 1

            while left <= right:
                next_char = word[left]
                next_is_alpha = next_char.isalpha()
                next_is_special = next_char.isalnum()
                if curr_is_alpha != next_is_alpha or curr_is_special != next_is_special:
                    break
                left += 1

            tokened.append(str(word[start_index:left]))

        return tokened

    def split_and_group(self, word: str, list_of_dicts: List):
        """
        Tokenizes a word based on alphanumeric or special character shifts. Then,
        apply abbreviations to find more tokens, and finally combines tokens
        if they form a valid word.

        :param word: Input string to separate into tokens.
        :type word: str
        :param list_of_dicts: List of dictionaries mapping abbreviations to brick classes.
        :type list_of_dicts: List

        :return: List of separated tokens.
        :rtype: List[str]
        """

        tokens = self.shift_split(word)
        arr = []
        combined_abbreviations = abbreviationsTool.make_combined_abbreviations(
            list_of_dicts
        )
        for group in tokens:
            if not group.isalnum():
                arr.append(group)
            elif combined_abbreviations(group) and not any(
                r.error for r in combined_abbreviations(group)
            ):
                parsed_abbrev = combined_abbreviations(group)[0].value
                arr.append(parsed_abbrev)
                remain = group[len(parsed_abbrev) :]
                if len(remain) > 0:
                    arr.extend(self.split_and_group(remain, list_of_dicts))
            else:
                arr.append(group)

        final_groups = []
        left = 0
        right = 1

        while right < len(arr):
            if wordChecker.check_word_validity(arr[left] + arr[right]) and (
                arr[left].isalpha() and arr[right].isalpha()
            ):
                final_groups.append(arr[left] + arr[right])
                left += 2
                right = left + 1
            else:
                final_groups.append(arr[left])
                left += 1
                right = left + 1
        if left < len(arr):
            final_groups.append(arr[left])

        return final_groups


codeLinter = Lint_Code()
tokenizer = Tokenizer()
