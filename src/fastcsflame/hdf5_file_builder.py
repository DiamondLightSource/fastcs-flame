import numpy as np
from numpy.typing import NDArray


class Hdf5FileBuilder:
    _version: str = "0.0.1"
    _url: str = ""
    _experiment_type: str = ""
    _beam_parameter_reliability: str = ""
    _detecter_channel_type: str = ""
    _wavelengths: NDArray = np.array(range(2044))

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
        pass

    def _create_definition_group(self, entry_group):
        pass

    def _create_instrument_group(self, entry_group):
        pass

    def _create_sample_group(self, entry_group):
        pass

    def _create_data_group(self, entry_group, data, times):
        pass
