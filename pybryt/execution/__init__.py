"""Submission execution internals for PyBryt"""

__all__ = ["check_time_complexity", "tracing_off", "tracing_on"]

import os
import dill
import nbformat

from nbconvert.preprocessors import ExecutePreprocessor
from copy import deepcopy
from tempfile import mkstemp
from typing import Any, List, Tuple, Optional
from textwrap import dedent

from .complexity import check_time_complexity, TimeComplexityResult
from .tracing import create_collector, TRACING_VARNAME, tracing_off, tracing_on
from ..preprocessors import IntermediateVariablePreprocessor
from ..utils import make_secret


NBFORMAT_VERSION = 4


def execute_notebook(nb: nbformat.NotebookNode, nb_path: str, addl_filenames: List[str] = [], 
        output: Optional[str] = None) -> Tuple[int, List[Tuple[Any, int]]]:
    """
    Executes a submission using ``nbconvert`` and returns the memory footprint.

    Takes in a notebook object and preprocesses it before running it through the 
    ``nbconvert.ExecutePreprocessor`` to execute it. The notebook writes the memory footprint, a 
    list of observed values and their timestamps, to a file, which is loaded using ``dill`` by this
    function. Errors during execution are ignored, and the executed notebook can be written to a 
    file using the ``output`` argument.

    Args:
        nb (``nbformat.NotebookNode``): the notebook to be executed
        nb_path (``str``): path to the notebook ``nb``
        addl_filenames (``list[str]``, optional): a list of additional files to trace inside
        output (``str``, optional): a file path at which to write the executed notebook

    Returns:
        ``tuple[int, list[tuple[object, int]]]``: the number of execution steps and the memory 
        footprint
    """
    nb = deepcopy(nb)
    preprocessor = IntermediateVariablePreprocessor()
    nb = preprocessor.preprocess(nb)

    secret = make_secret()
    _, observed_fp = mkstemp()
    nb_dir = os.path.abspath(os.path.split(nb_path)[0])

    first_cell = nbformat.v4.new_code_cell(dedent(f"""\
        import sys
        from pybryt.execution import create_collector
        observed_{secret}, cir = create_collector(addl_filenames={addl_filenames})
        sys.settrace(cir)
        {TRACING_VARNAME} = True
        %cd {nb_dir}
    """))

    last_cell = nbformat.v4.new_code_cell(dedent(f"""\
        sys.settrace(None)
        import dill
        from pybryt.utils import filter_picklable_list
        filter_picklable_list(observed_{secret})
        with open("{observed_fp}", "wb+") as f:
            dill.dump(observed_{secret}, f)
    """))

    nb['cells'].insert(0, first_cell)
    nb['cells'].append(last_cell)

    ep = ExecutePreprocessor(timeout=1200, allow_errors=True)

    ep.preprocess(nb)

    if output:
        with open(output, "w+") as f:
            nbformat.write(nb, f)

    with open(observed_fp, "rb") as f:
        observed = dill.load(f)

    os.remove(observed_fp)

    n_steps = max([t[1] for t in observed])

    return n_steps, observed
