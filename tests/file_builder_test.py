import h5py
import numpy as np
import pytest

from fastcsflame.hdf5_file_builder import Hdf5FileBuilder


# TODO: Add some sort of clean up in tests that close this incase of an error
# Otherwise all tests after will error too
# Also delete file after tests
@pytest.fixture
def basic_file():
    fb = Hdf5FileBuilder()

    data = np.array([1000 for i in range(2044)])
    times = np.array([np.datetime64("2026-06-26T11:20:50")])

    # Is CI not going to like me trying to make files??
    file = fb.create_h5_file("./", "data.nxs", "", "", "", data, times)
    yield file
    file.close()


def test_entry_structure(basic_file):
    entry_group = basic_file["ENTRY"]
    assert isinstance(entry_group, h5py.Group)

    title_field = entry_group["title"]
    assert isinstance(title_field, h5py.Dataset)
    start_time_field = entry_group["start_time"]
    assert isinstance(start_time_field, h5py.Dataset)
    end_time_field = entry_group["end_time"]
    assert isinstance(end_time_field, h5py.Dataset)
    experiment_type_field = entry_group["experiment_type"]
    assert isinstance(experiment_type_field, h5py.Dataset)


def test_definition_structure(basic_file):
    entry_group = basic_file["ENTRY"]

    definition_field = entry_group["definition"]
    assert isinstance(definition_field, h5py.Dataset)
    assert "@version" in definition_field.attrs
    assert "@URL" in definition_field.attrs


def test_instrument_structure(basic_file):
    entry_group = basic_file["ENTRY"]

    instrument_group = entry_group["INSTRUMENT"]
    assert isinstance(instrument_group, h5py.Group)

    beam_type_group = instrument_group["beam_TYPE"]
    assert isinstance(beam_type_group, h5py.Group)
    detector_type_group = instrument_group["detector_TYPE"]
    assert isinstance(detector_type_group, h5py.Group)

    parameter_reliability_field = beam_type_group["parameter_reliability"]
    assert isinstance(parameter_reliability_field, h5py.Dataset)
    detector_channel_type_field = detector_type_group["detector_channel_type"]
    assert isinstance(detector_channel_type_field, h5py.Dataset)


def test_sample_structure(basic_file):
    entry_group = basic_file["ENTRY"]

    sample_group = entry_group["SAMPLE"]
    assert isinstance(sample_group, h5py.Group)

    name_field = sample_group["name"]
    assert isinstance(name_field, h5py.Dataset)
    sample_id_field = sample_group["sample_id"]
    assert isinstance(sample_id_field, h5py.Dataset)


def test_data_structure(basic_file):
    entry_group = basic_file["ENTRY"]

    data_group = entry_group["DATA"]
    assert isinstance(data_group, h5py.Group)

    assert "axes" in data_group.attrs
    assert "signal" in data_group.attrs

    dataset = data_group["DATA"]
    assert isinstance(dataset, h5py.Dataset)

    time_axis = data_group["TIME_AXIS"]
    assert isinstance(time_axis, h5py.Dataset)
    assert "long_name" in time_axis.attrs

    wavelength_axis = data_group["WAVELENGTH_AXIS"]
    assert isinstance(wavelength_axis, h5py.Dataset)
    assert "long_name" in wavelength_axis.attrs
