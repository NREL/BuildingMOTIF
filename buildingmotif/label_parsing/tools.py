import subprocess

import enchant
from combinators import equip_abbreviations, point_abbreviations, make_combined_abbreviations

class Lint_Code:
    """
    Runs black in a subprocess to lint code
    """

    def _run(self, filepath):
        subprocess.run(
            f"black {filepath}",
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            timeout=3,
            check=False,
        )


class Check_Valid_Word:
    """
    Checks word validity using enchant package, used for one way of detecting constants
    """

    def check_word_validity(self, input_str: str):
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

    def split_and_group(self, word: str, list_of_dicts):
        """
        Tokenizes a word based on alphanumeric or special character shifts. Then,
        apply abbreviations to find more tokens, and combines tokens
        if they form a valid word according to enchant.
        """

        tokens = self.shift_split(word)
        arr = []
        combined_abbreviations = make_combined_abbreviations(list_of_dicts)
        for group in tokens:
            if not group.isalnum():
                arr.append(group)
            elif combined_abbreviations(group) and not any(r.error for r in combined_abbreviations(group)):
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
        #print(final_groups)
        return final_groups


codeLinter = Lint_Code()
tokenizer = Tokenizer()