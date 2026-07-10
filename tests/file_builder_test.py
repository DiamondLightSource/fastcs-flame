from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import NDArray
from pytest import fixture

from fastcsflame.file_builder import FileBuilder


@dataclass
class FileParameters:
    file_path: str
    file_name: str
    wavelength_array: NDArray[np.float64]
    data: NDArray[np.int64]


BASIC_DUMMY_PATH = "/data"
BASIC_DUMMY_NAME = "data"
EXTENDED_DUMMY_PATH = "/dls/science/more"
ALTERNATE_DUMMY_NAME = "dt"
BASIC_WAVLENGTH_ARRAY = np.array(range(2044), dtype=np.float64)
ALTERNATE_WAVELENGTH_ARRAY = np.array(range(1000), dtype=np.float64)
BASIC_DATA_ARRAY = np.array([range(2044)])
ALTERNATE_DATA_ARRAY = np.array([range(1000)])
LARGER_DATA_ARRAY = np.array([[i + j for j in range(2044)] for i in range(10)])
EMPTY_DATA_ARRAY = np.array([])


@fixture(
    params=[
        # Basic file
        FileParameters(
            BASIC_DUMMY_PATH,
            BASIC_DUMMY_NAME,
            BASIC_WAVLENGTH_ARRAY,
            BASIC_DATA_ARRAY,
        ),
        # Test extended file path and different name
        FileParameters(
            EXTENDED_DUMMY_PATH,
            ALTERNATE_DUMMY_NAME,
            BASIC_WAVLENGTH_ARRAY,
            BASIC_DATA_ARRAY,
        ),
        # Test different wavelengths
        FileParameters(
            BASIC_DUMMY_PATH,
            BASIC_DUMMY_NAME,
            ALTERNATE_WAVELENGTH_ARRAY,
            ALTERNATE_DATA_ARRAY,
        ),
        # Test more rows of data
        FileParameters(
            BASIC_DUMMY_PATH,
            BASIC_DUMMY_NAME,
            BASIC_WAVLENGTH_ARRAY,
            LARGER_DATA_ARRAY,
        ),
        # Test no rows of data
        FileParameters(
            BASIC_DUMMY_PATH,
            BASIC_DUMMY_NAME,
            BASIC_WAVLENGTH_ARRAY,
            EMPTY_DATA_ARRAY,
        ),
    ]
)
def h5file(tmp_path, request):
    params = request.param

    params.file_path = str(tmp_path) + params.file_path

    Path(params.file_path).mkdir(parents=True, exist_ok=True)

    fb = FileBuilder(params.wavelength_array)
    fb.create_file(params.file_path, params.file_name)

    for data_row in params.data:
        fb.add_scan(data_row)
    fb.close_file()

    return params


def test_creation(h5file):
    params = h5file

    # Test the file is created in the correct place
    file = h5py.File(f"{params.file_path}/{params.file_name}.h5", "r")
    assert isinstance(file, h5py.File)


def test_structure(h5file):
    params = h5file
    file = h5py.File(f"{params.file_path}/{params.file_name}.h5", "r")

    entry_group = file["entry"]
    assert isinstance(entry_group, h5py.Group)

    data_group = entry_group["data"]
    assert isinstance(data_group, h5py.Group)

    dataset = data_group["data"]
    assert isinstance(dataset, h5py.Dataset)

    wavelength_axis = data_group["wavelength_axis"]
    assert isinstance(wavelength_axis, h5py.Dataset)

    assert "axes" in data_group.attrs
    assert "signal" in data_group.attrs
    assert "long_name" in wavelength_axis.attrs


def test_values(h5file):
    params = h5file
    file = h5py.File(f"{params.file_path}/{params.file_name}.h5", "r")

    dataset = file["entry/data/data"]
    assert isinstance(dataset, h5py.Dataset)

    if len(params.data) != 0:
        assert np.array_equal(np.array(dataset), params.data)

    wavlength_axis = file["entry/data/wavelength_axis"]
    assert isinstance(wavlength_axis, h5py.Dataset)

    assert np.array_equal(np.array(wavlength_axis), params.wavelength_array)
