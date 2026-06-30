import h5py
from numpy.typing import NDArray

from fastcsflame.hdf5_file_builder import Hdf5FileBuilder


class DummyHdf5FileBuilder(Hdf5FileBuilder):
    create_h5_file_destination_arg: str | None = None
    create_h5_file_filename_arg: str | None = None
    create_h5_file_title_arg: str | None = None
    create_h5_file_sample_name_arg: str | None = None
    create_h5_file_sample_id_arg: str | None = None
    create_h5_file_data_arg: NDArray | None = None
    create_h5_file_times_arg: NDArray | None = None

    def create_h5_file(
        self,
        destination: str,
        filename: str,
        title: str,
        sample_name: str,
        sample_id: str,
        data: NDArray,
        times: NDArray,
    ) -> h5py.File:

        self.create_h5_file_destination_arg = destination
        self.create_h5_file_filename_arg = filename
        self.create_h5_file_title_arg = title
        self.create_h5_file_sample_name_arg = sample_name
        self.create_h5_file_sample_id_arg = sample_id
        self.create_h5_file_data_arg = data
        self.create_h5_file_times_arg = times

        print("in create call")
        print(sample_name)

        return h5py.File(destination + filename, "w")
