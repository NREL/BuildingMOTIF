from uuid import uuid4

from IPython.core.error import StdinNotImplementedError


def notebook_input(prompt, default=None):
    try:
        return input(prompt)
    except StdinNotImplementedError:
        if default:
            return default
        return str(uuid4())
