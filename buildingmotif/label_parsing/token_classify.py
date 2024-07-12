from typing import List

from langchain.output_parsers import PydanticOutputParser
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from buildingmotif.label_parsing import usage
from buildingmotif.label_parsing.tools import tokenizer

llm = Ollama(model="llama3")


class Token_Prediction(BaseModel):
    """
    Class that LLM populates with tokens and corresponding classifications: constant, delimiter, abbreviations, or identifier
    """

    token: str = Field(description="a token from token string")
    classification: str = Field(
        description="predicted classification: constant, delimiter, abbreviations, or identifier"
    )


class LLM_Token_Predictions(BaseModel):
    """
    Class of a List of Token_Prediction for each token.
    """

    predictions: List[Token_Prediction] = Field(
        description="list of predicted classes for each token"
    )


parser = PydanticOutputParser(pydantic_object=LLM_Token_Predictions)


def classify_tokens_with_llm(user_input: str, list_of_dicts: List, num_tries: int):
    """
    Uses LLM Ollama3 to classify each token as either a constant, abbreviation, identifier, or delimiter.
    Returns List of Token_Prediction, which has a token and classification field as predicted by the LLM.

    :param user_input: Building point label string.
    :type user_input: str
    :param list_of_dicts: List of dictionaries mapping abbreviations to brick classes.
    :type list_of_dicts: List
    :param num_tries: Maximum number of attempts for LLM to create List of Token_Prediction.
    :type num_tries: int

    :return: List of Token_Prediction.
    :rtype: List
    """

    tokens_str_list = str(tokenizer.split_and_group(user_input, list_of_dicts))

    headers_to_split_on = [
        ("## `string`", "Header 1"),
        ("## `rest`", "Header 2"),
        ("## `regex`", "Header 3"),
        ("## `choice`", "Header 4"),
        ("## `constant`", "Header 5"),
        ("## `sequence`", "Header 6"),
        ("## `many`", "Header 7"),
        ("## `maybe`", "Header 8"),
        ("## `until`", "Header 9"),
        ("## `extend_if_match`", "Header 10"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on, strip_headers=False
    )
    md_header_splits = markdown_splitter.split_text(
        usage.usage_markdown
    )  # file_content contains detailed description of each parser class from combinators.py

    chunk_size = 200
    chunk_overlap = 0
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    splits = text_splitter.split_documents(md_header_splits)

    class_mapping = f"""
    Try to classify each token in {tokens_str_list}, as either a
    constant, identifier, delimeter, or abreviations. Tokens are from {tokens_str_list}.
    
    A constant token is usually a valid word, to represent some sort of Class. Constants are NEVER numbers.
    A constant token is usually a valid word, to represent some sort of Class. Constants are NEVER numbers.
    A constant token is usually a valid word, to represent some sort of Class. Constants are NEVER numbers.
    A constant token is usually a valid word, to represent some sort of Class. Constants are NEVER numbers.

    A delimiter token is a special character.

    An identifier token is a sequence of alphanumeric characters, usually a shorter sequence, and is NOT a valid word. It can be a NUMBER.
    An identifier token is a sequence of alphanumeric characters, usually a shorter sequence, and is NOT a valid word. It can be a NUMBER.
    An identifier token is a sequence of alphanumeric characters, usually a shorter sequence, and is NOT a valid word. It can be a NUMBER.

    An abbreviations usually stands for another word and is usally only made up of uppercase letters.

    each token should ONLY be matched to a class, either: Constant, Identifier, Abbreviations, or Delimiter.
    each token should ONLY be matched to a class, either: Constant, Identifier, Abbreviations, or Delimiter.
    each token should ONLY be matched to a class, either: Constant, Identifier, Abbreviations, or Delimiter.

    No extra output. Do not provide explanations.
    No extra output. Do not provide explanations.
    No extra output. Do not provide explanations.

    I will give you a $100000000 dollar tip if you follow my instructions and can classify {tokens_str_list}
    """

    prompt = PromptTemplate(
        template="""Answer the user query with context at {examples}
    {format_instructions}\n{query}\n""",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    curr_tries = 0
    while curr_tries < num_tries:
        try:
            resp = chain.invoke({"query": class_mapping, "examples": splits})
            break
        except Exception as e:
            print(e)
            resp = None
        finally:
            curr_tries += 1

    return resp
