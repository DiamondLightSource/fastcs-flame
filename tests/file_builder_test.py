import h5py
import numpy as np

from fastcsflame.hdf5_file_builder import Hdf5FileBuilder


def test_creation(tmp_path):
    wavelengths = np.array(range(2044))

    fb = Hdf5FileBuilder(wavelengths)
    fb.create_file(tmp_path, "data")
    data = np.zeros_like(wavelengths)
    fb.add_scan(data)
    fb.close_file()

    # Test the file is created in the correct place
    file = h5py.File(f"{tmp_path}/data.h5", "r")
    assert isinstance(file, h5py.File)


def test_structure(tmp_path):
    wavelengths = np.array(range(2044))

    fb = Hdf5FileBuilder(wavelengths)
    fb.create_file(tmp_path, "data")
    data = np.zeros_like(wavelengths)
    fb.add_scan(data)
    fb.close_file()

    file = h5py.File(f"{tmp_path}/data.h5", "r")
    assert isinstance(file, h5py.File)

    entry_group = file["ENTRY"]
    assert isinstance(entry_group, h5py.Group)

    data_group = entry_group["DATA"]
    assert isinstance(data_group, h5py.Group)

    dataset = data_group["Data"]
    assert isinstance(dataset, h5py.Dataset)

    wavelength_axis = data_group["WAVELENGTH_AXIS"]
    assert isinstance(wavelength_axis, h5py.Dataset)

    assert "axes" in data_group.attrs
    assert "signal" in data_group.attrs
    assert "long_name" in wavelength_axis.attrs


def test_values(tmp_path):
    wavelengths = np.array(range(2044))

    fb = Hdf5FileBuilder(wavelengths)
    fb.create_file(tmp_path, "data")
    datas = []
    iterations = 5
    for _ in range(iterations):
        data = np.random.randint(900, high=1100, size=wavelengths.shape)
        fb.add_scan(data)
        datas.append(data)
    fb.close_file()

    # Test the file is created in the correct place
    file = h5py.File(f"{tmp_path}/data.h5", "r")
    assert isinstance(file, h5py.File)

    dataset = file["ENTRY/DATA/Data"]
    assert isinstance(dataset, h5py.Dataset)

    assert np.array_equal(np.array(dataset), np.array(datas))

    wavlength_axis = file["ENTRY/DATA/WAVELENGTH_AXIS"]
    assert isinstance(wavlength_axis, h5py.Dataset)

    assert np.array_equal(np.array(wavlength_axis), np.array(wavelengths))
