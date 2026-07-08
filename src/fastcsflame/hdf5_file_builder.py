import h5py
import numpy as np
from numpy.typing import NDArray


class Hdf5FileBuilder:
    _wavelengths: NDArray[np.float64]
    file: h5py.File | None = None
    scans_added: int = 0

    string_dtype = h5py.string_dtype(encoding="utf-8")

    def __init__(self, wavelengths: NDArray[np.float64]):
        self._wavelengths = wavelengths

    def create_file(self, file_path: str, file_name: str):
        self.file = h5py.File(f"{file_path}/{file_name}.h5", "w")

        entry_group = self.file.create_group("entry")

        self._create_data_group(entry_group)
        self._create_instrument_group(entry_group)

    def _create_data_group(self, parent_group: h5py.Group):
        data_group = parent_group.create_group("data")

        # Dataset starts empty but will have scan data added to it as scans are taken
        # maxshape with first argument None allows this
        data_group.create_dataset(
            "data",
            shape=(0, len(self._wavelengths)),
            dtype=np.int64,
            chunks=True,
            maxshape=(None, len(self._wavelengths)),
        )

        data_group.attrs["axes"] = "Scan x Wavelength"
        data_group.attrs["signal"] = "Intensity"

        wavelength_axis = data_group.create_dataset(
            "wavelength_axis", data=self._wavelengths
        )
        wavelength_axis.attrs["long_name"] = "Wavelength"
        wavelength_axis.attrs["units"] = "nm"

        self.scans_added = 0

    def _create_instrument_group(self, parent_group: h5py.Group):
        instrument_group = parent_group.create_group("instrument")

        instrument_group.create_dataset(
            "make", data=np.array(["Flame Miniature Spectrometer"])
        )
        instrument_group.create_dataset("model", data=np.array(["FLAME-S"]))
        instrument_group.create_dataset("manufacturer", data=np.array(["OceanOptics"]))

    def add_scan(self, data: NDArray[np.int64]):

        if self.file is None:
            print("File not created")
            return

        dataset = self.file["entry/data/data"]
        if not isinstance(dataset, h5py.Dataset):
            print("Couldnt find dataset")
            return

        # Adds an extra space for the new scan data
        dataset.resize(self.scans_added + 1, axis=0)
        # Places new scan data at the end of the array
        dataset[self.scans_added] = data

        self.scans_added += 1

    def close_file(self):
        if self.file is None:
            print("file not open")
            return

        self.file.close()
        self.file = None
