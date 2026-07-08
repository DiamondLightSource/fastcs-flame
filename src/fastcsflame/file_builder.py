import h5py
import numpy as np
from numpy.typing import NDArray


class NoOpenFileError(Exception):
    pass


class ScanLengthError(Exception):
    pass


class FileBuilder:
    """
    Builds h5 files containing data collected from the Flame
    """

    _wavelengths: NDArray[np.float64]
    file: h5py.File | None = None
    scans_added: int = 0

    string_dtype = h5py.string_dtype(encoding="utf-8")

    def __init__(self, wavelengths: NDArray[np.float64]):
        """
        wavelengths: An array of wavelength values in nanometers
            Represents wavelengths of intensity data points collected by flame
            Should be the same length as the scan data collected by flame
        """
        self._wavelengths = wavelengths

    def create_file(self, file_path: str, file_name: str):
        """
        Creates and structures an h5 file for Flame data
        file_path: Where to create the file
            Both relative and absolute file paths are valid
            Do not include final /
        file_name: What to call the file
            Do not include extension
        If a h5 file exist at the file_path location with a matching name it will
        be replaced without warning
        This method may be called multiple times from this class to create multiple
        files
        """
        self.file = h5py.File(f"{file_path}/{file_name}.h5", "w")

        entry_group = self.file.create_group("entry")

        self._create_data_group(entry_group)
        self._create_instrument_group(entry_group)

    def _create_data_group(self, parent_group: h5py.Group):
        """
        Creates and structures the data group of the h5 file
        parent_group: Group to create the data group under
        """
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
        """
        Creates and structures the instrument group of the h5 file
        parent_group: Group to create the instrument group under
        """
        instrument_group = parent_group.create_group("instrument")

        instrument_group.create_dataset(
            "make", data=np.array(["Flame Miniature Spectrometer"])
        )
        instrument_group.create_dataset("model", data=np.array(["FLAME-S"]))
        instrument_group.create_dataset("manufacturer", data=np.array(["OceanOptics"]))

    def add_scan(self, data: NDArray[np.int64]):
        """
        Adds scan data to the last created h5 file
        data: Scan data from the flame
        raises:
            NoOpenFileError
                When no file has been created or the previously created file was closed
            FileNotFoundError
                When the scan data dataset couldnt be found in the h5 file
            ScanLengthError
                When scan data length does not match wavelength array length
        """

        if self.file is None:
            raise NoOpenFileError(
                "No file has been created or last created file was closed.\n"
                "Nowhere to add scan to"
            )

        dataset_path = "entry/data/data"
        dataset = self.file[dataset_path]
        if not isinstance(dataset, h5py.Dataset):
            raise FileNotFoundError(
                f"Could not find dataset in h5 file at: {dataset_path}"
            )

        if self._wavelengths.shape[0] != data.shape[0]:
            raise ScanLengthError(
                "Scan data length does not match wavelength array length.\n"
                f"Scan data length: {data.shape[0]} \n"
                f"Wavelength array length: {self._wavelengths.shape[0]} \n"
                "Could not add data to file"
            )

        # Adds an extra space for the new scan data
        dataset.resize(self.scans_added + 1, axis=0)
        # Places new scan data at the end of the array
        dataset[self.scans_added] = data

        self.scans_added += 1

    def close_file(self):
        """
        Closes last created h5 file
        raises:
            NoOpenFileError
                When no file has been created or the previously created file was closed
        """
        if self.file is None:
            raise NoOpenFileError(
                "No file has been created or last created file was closed.\n"
                "No file to close"
            )

        self.file.close()
        self.file = None
