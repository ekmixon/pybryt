""""""

import sys
import inspect
import numpy as np

from unittest import mock

from pybryt import *
from pybryt.execution import create_collector, TRACING_VARNAME

from .utils import generate_mocked_frame


__PYBRYT_TRACING__ = False


def test_trace_function():
    """
    """
    np.random.seed(42)
    
    tracked_filepath = "/path/to/tracked/file.py"

    frame = generate_mocked_frame("<ipython-abc123>", "foo", 3)
    observed, cir = create_collector(addl_filenames=[tracked_filepath])

    arr = np.random.uniform(-100, 100, size=(100, 100))
    cir(frame, "return", arr)
    assert len(observed) == 1
    assert np.allclose(observed[0][0], arr)
    assert observed[0][1] == 1

    # test value in skip_types
    cir(frame, "return", type(1))
    assert len(observed) == 1

    # test pickling error
    with mock.patch("dill.dumps") as mocked_dumps:
        mocked_dumps.side_effect = Exception()
        cir(frame, "return", 1)
    
    assert len(observed) == 1

    frame = generate_mocked_frame(
        "<ipython-abc123>", "foo", 3, {"data": arr}
    )

    # check line processing working
    with mock.patch("linecache.getline") as mocked_linecache:

        # check eval call for attributes
        mocked_linecache.return_value = "data.T"
        cir(frame, "line", None)
        assert len(observed) == 2
        assert np.allclose(observed[1][0], arr.T)
        assert observed[1][1] == 4

        # check failed eval call for attributes
        mocked_linecache.return_value = "data.doesnt_exist"
        cir(frame, "line", None)
        assert len(observed) == 2

        # check looking in frame locals + globals
        frame.f_globals["more_data"] = np.random.uniform(-100, 100, size=(100, 100))
        frame.f_locals["more_data"] = np.random.uniform(-100, 100, size=(100, 100))
        mocked_linecache.return_value = "more_data"
        cir(frame, "line", None)
        assert len(observed) == 3
        assert np.allclose(observed[2][0], frame.f_locals["more_data"])
        assert observed[2][1] == 6

        # check that we track assignment statements on function return
        mocked_linecache.return_value = "even_more_data = more_data ** 2"
        cir(frame, "line", None)
        assert len(observed) == 3

        mocked_linecache.return_value = "even_more_data_2 = more_data ** 3"
        cir(frame, "line", None)
        assert len(observed) == 3

        frame.f_locals["even_more_data"] = frame.f_locals["more_data"] ** 2
        frame.f_globals["even_more_data_2"] = frame.f_locals["more_data"] ** 3
        mocked_linecache.return_value = ""
        cir(frame, "return", None)
        assert len(observed) == 6
        assert observed[3][0] is None
        assert observed[3][1] == 9
        assert np.allclose(observed[4][0], frame.f_locals["more_data"] ** 2)
        assert observed[4][1] == 7
        assert np.allclose(observed[5][0], frame.f_locals["more_data"] ** 3)
        assert observed[5][1] == 8

        # check that skip_types respected
        frame.f_locals["none_type"] = type(None)
        mocked_linecache.return_vaue = "none_type"
        cir(frame, "line", None)
        assert len(observed) == 6

        # check that addl_filenames respected
        frame = generate_mocked_frame(tracked_filepath, "bar", 100, f_back=frame)
        frame.f_locals["data"] = arr
        mocked_linecache.return_value = "arr = -1 * data"
        cir(frame, "line", None)
        frame.f_locals["arr"] = -1 * arr
        cir(frame, "return", None) # run a return since arr shows up in vars_not_found
        assert len(observed) == 7
        assert np.allclose(observed[6][0], -1 * arr)
        assert observed[6][1] == 12
    
    # check that IPython child frame return values are tracked
    frame = generate_mocked_frame("/path/to/file.py", "bar", 100, f_back=frame)
    cir(frame, "line", None)
    assert len(observed) == 7

    cir(frame, "return", np.exp(arr))
    assert len(observed) == 8
    assert np.allclose(observed[7][0], np.exp(arr))
    assert observed[7][1] == 12


def test_tracing_control():
    """
    """
    global __PYBRYT_TRACING__
    trace = lambda frame, event, arg: trace

    __PYBRYT_TRACING__ = True
    with mock.patch("sys.settrace") as mocked_settrace:
        tracing_off()
        mocked_settrace.assert_called()

    with mock.patch("sys.settrace") as mocked_settrace:
        tracing_on()
        mocked_settrace.assert_called()

    __PYBRYT_TRACING__ = False
    with mock.patch("sys.settrace") as mocked_settrace:
        tracing_off()
        mocked_settrace.assert_not_called()

    with mock.patch("sys.settrace") as mocked_settrace:
        tracing_on()
        mocked_settrace.assert_not_called()

    # assert inspect.currentframe().f_trace is not trace
