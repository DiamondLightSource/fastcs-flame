import h5py
import numpy as np
from numpy.typing import NDArray


class Hdf5FileBuilder:
    _wavelengths: NDArray

    string_dtype = h5py.string_dtype(encoding="utf-8")
    # This seems like a really stupid way to do this but its what they
    # do in the documentation
    # Maybe set it in __init__ or create_h5_file when we actually have time data??
    datetime_dtype = h5py.opaque_dtype(np.array([np.datetime64("2005-02-25")]).dtype)

    file: h5py.File | None = None
    scans_added: int = 0

    def __init__(self, wavelengths: list[int]):
        self._wavelengths = np.array(wavelengths)

    def create_file(self, file_path: str, file_name: str):
        self.file = h5py.File(f"{file_path}/{file_name}.h5", "w")

        entry_group = self.file.create_group("ENTRY")
        # instrument = entry_group.create_group("INSTRUMENT")
        data_group = entry_group.create_group("DATA")

        data_group.create_dataset(
            "Data",
            shape=(0, len(self._wavelengths)),
            dtype=np.int64,
            chunks=True,
            maxshape=(None, len(self._wavelengths)),
        )

        data_group.attrs["axes"] = "Scan x Wavelength"
        data_group.attrs["signal"] = "Intensity"

        wavelength_axis = data_group.create_dataset(
            "WAVELENGTH_AXIS", data=self._wavelengths
        )
        wavelength_axis.attrs["long_name"] = "Wavelength"

        self.scans_added = 0

    def add_scan(self, raw_data: list[int]):

        if self.file is None:
            print("File not created")
            return

        data = np.array(raw_data)

        dataset = self.file["ENTRY/DATA/Data"]
        if not isinstance(dataset, h5py.Dataset):
            print("Couldnt find dataset")
            return

        dataset.resize(self.scans_added + 1, axis=0)
        dataset[self.scans_added] = data

        self.scans_added += 1

    def close_file(self):
        if self.file is None:
            print("file not open")
            return

        self.file.close()
        self.file = None
