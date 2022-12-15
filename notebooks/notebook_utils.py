from uuid import uuid4

from IPython.core.error import StdinNotImplementedError


def notebook_input(prompt, default=None):
    """
    Input function that allows use of input in notebooks, which are run by nbmake.
    :param prompt: input prompt
    :param default: default value if run by nbmake (uuid4 string if not specified)
    """
    try:
        return input(prompt)
    except StdinNotImplementedError:
        if default:
            return default
        return str(uuid4())
