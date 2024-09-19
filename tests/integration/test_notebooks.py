import sys
from pathlib import Path

import pytest
from nbmake.nb_result import NotebookResult
from nbmake.nb_run import NotebookRun


@pytest.mark.integration
def test_notebook(notebook: Path):
    run = NotebookRun(notebook, 600)
    res: NotebookResult = run.execute()
    if res.error is not None:
        # Print error from notebook
        print(res.error.summary, file=sys.stderr)
        print(res.error.trace, file=sys.stderr)

        # Fail the test
        pytest.fail(f"Failing Notebook: {notebook}", pytrace=False)
