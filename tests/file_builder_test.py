import numpy as np
import pytest

from fastcsflame.hdf5_file_builder import Hdf5FileBuilder


@pytest.fixture
def basic_file():
    fb = Hdf5FileBuilder()

    data = np.array([1000 for i in range(2044)])
    times = np.array([np.datetime64("2026-06-26T11:20:50")])

    # Is CI not going to like me trying to make files??
    file = fb.create_h5_file("./", "data.nxs", "", "", "", data, times)
    return file


def test_entry_structure(basic_file):
    pass


def test_definition_structure(basic_file):
    pass


def test_instrument_structure(basic_file):
    pass


def test_sample_structure(basic_file):
    pass


def test_data_structure(basic_file):
    pass
