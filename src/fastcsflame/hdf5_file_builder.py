import h5py
import numpy as np
from numpy.typing import NDArray


class Hdf5FileBuilder:
    _definition: str = ""
    _version: str = "0.0.1"
    _url: str = ""
    _experiment_type: str = ""
    _beam_parameter_reliability: str = ""
    _detecter_channel_type: str = ""
    _wavelengths: NDArray = np.array(range(2044))

    string_dtype = h5py.string_dtype(encoding="utf-8")
    # This seems like a really stupid way to do this but its what they
    # do in the documentation
    # Maybe set it in __init__ or create_h5_file when we actually have time data??
    datetime_dtype = h5py.opaque_dtype(np.array([np.datetime64("2005-02-25")]).dtype)

    def __init__(self):
        pass

    def create_h5_file(
        self,
        destination: str,
        filename: str,
        title: str,
        sample_name: str,
        sample_id: str,
        data: NDArray,
        times: NDArray,
    ):
        # NOTE: times HAS to be an array of np.datetime64 NOT normal datetime (I think)
        # TODO: check file name ends with .h5 OR .hdf5
        # Check destination ends in /??
        # Check if existing file exists??
        h5file = h5py.File(destination + filename, "w")

        entry_group = h5file.create_group("ENTRY")

        entry_group.create_dataset("title", dtype=self.string_dtype, data=[title])
        entry_group.create_dataset("start_time", data=self.time_typecast(times[0]))
        entry_group.create_dataset("end_time", data=self.time_typecast(times[-1]))
        entry_group.create_dataset(
            "experiment_type", dtype=self.string_dtype, data=[self._experiment_type]
        )

        self._create_definition_dataset(entry_group)
        self._create_instrument_group(entry_group)
        self._create_sample_group(entry_group, sample_name, sample_id)
        self._create_data_group(entry_group, data, times)

        return h5file

    def time_typecast(self, time_value: np.datetime64):
        # Stupid
        return np.array([time_value]).astype(self.datetime_dtype)

    def _create_definition_dataset(self, entry_group: h5py.Group):
        definition_dataset = entry_group.create_dataset(
            "definition", dtype=self.string_dtype, data=[self._definition]
        )
        definition_dataset.attrs["@version"] = self._version
        definition_dataset.attrs["@URL"] = self._url

    def _create_instrument_group(self, entry_group: h5py.Group):
        instrument_group = entry_group.create_group("INSTRUMENT")
        beam_group = instrument_group.create_group("beam_TYPE")
        detector_group = instrument_group.create_group("detector_TYPE")

        beam_group.create_dataset(
            "parameter_reliability",
            dtype=self.string_dtype,
            data=[self._beam_parameter_reliability],
        )
        detector_group.create_dataset(
            "detector_channel_type",
            dtype=self.string_dtype,
            data=[self._detecter_channel_type],
        )

    def _create_sample_group(
        self, entry_group: h5py.Group, sample_name: str, sample_id: str
    ):
        sample_group = entry_group.create_group("SAMPLE")
        sample_group.create_dataset("name", dtype=self.string_dtype, data=[sample_name])
        sample_group.create_dataset("name", dtype=self.string_dtype, data=[sample_id])

    def _create_data_group(
        self, entry_group: h5py.Group, data: NDArray, times: NDArray
    ):
        data_group = entry_group.create_group("DATA")
        data_group.attrs["axes"] = "Time x Wavelength"
        data_group.attrs["signal"] = "Intensity"
        data_group.create_dataset("DATA", data)

        time_axis = data_group.create_dataset(
            "TIME_AXIS", times.astype(self.datetime_dtype)
        )
        time_axis.attrs["long_name"] = "Time"

        wavelength_axis = data_group.create_dataset(
            "WAVELENGTH_AXIS", self._wavelengths
        )
        wavelength_axis.attrs["long_name"] = "Wavelength"
