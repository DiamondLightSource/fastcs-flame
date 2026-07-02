import numpy as np
from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String, Waveform
from fastcs.logging import logger
from fastcs.methods.command import command

from fastcsflame.flame_controller_attributes import (
    DummyBoolIO,
    DummyBoolIORef,
    DummyStrIO,
    DummyStrIORef,
    IntegrationTimeIORef,
    ScanDataIORef,
    SpectrometerIntIO,
    SpectrometerScanIO,
)
from fastcsflame.hdf5_file_builder import Hdf5FileBuilder
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError

# In practice these numbers (or numbers for each individual pixels wavelength)
# Should be calculated in calibration
# This is just the max and min wavelength from the manual
LOWEST_WAVELENGTH = 190
HIGHEST_WAVELENGTH = 1100
# Should be 2048 in theory but 2044 in practice
SCAN_DATA_LENGTH = 2044


class FlameController(Controller):
    """
    FastCS controller for an OceanOptics Flame spectrometer
    """

    spec_tel_obj: SpecTel

    integration_time: AttrRW[int, IntegrationTimeIORef]

    sample_name: AttrRW[str, DummyStrIORef]
    sample_id: AttrRW[str, DummyStrIORef]
    capture: AttrRW[bool, DummyBoolIORef]

    # Scan data from spectrometer
    scan_data: AttrR[np.ndarray, ScanDataIORef]

    file_builder: Hdf5FileBuilder

    def __init__(
        self,
        ip: str,
        port: int,
        default_file_path: str = ".",
        default_file_name: str = "data",
    ):
        """
        Creates controller object
        Creates SpectrometerTelecommunicator object but does NOT connect to it
        ip: IP address of the device the spectrometer is connected to
            example: "192.168.0.1"
        port: Port of the device the spectrometer is communicating on
        output_data_file_path: File to store acquired data in
            If a file does not exist one will be created
            If a file does exist it will be overwritten
        default_acquisition_period: Default value for acquisition period (seconds)
        default_total_scans: Default value for scans to perform in acquisition period
        """
        self.spec_tel_obj = SpecTel(ip, port)
        super().__init__(
            ios=[
                SpectrometerIntIO(),
                DummyBoolIO(),
                DummyStrIO(),
                SpectrometerScanIO(),
            ]
        )

        self.file_builder = Hdf5FileBuilder(
            np.linspace(LOWEST_WAVELENGTH, HIGHEST_WAVELENGTH, SCAN_DATA_LENGTH)
        )

        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )

        self.nexus_save_file_path = AttrRW(
            String(), io_ref=DummyStrIORef(default_file_path)
        )
        self.nexus_save_file_name = AttrRW(
            String(), io_ref=DummyStrIORef(default_file_name)
        )
        self.capture = AttrRW(Bool(), io_ref=DummyBoolIORef(False))
        self.capture.add_on_update_callback(self.on_capture_change)

        self.scan_data = AttrR(
            Waveform(int, shape=(SCAN_DATA_LENGTH,)),
            io_ref=ScanDataIORef(self.spec_tel_obj),
        )

    async def connect(self):
        await super().connect()
        await self.spec_tel_obj.connect()

    @command()
    async def single_scan(self):
        """
        Conducts a single scan using the spectrometer
        Stores scan data in ScanData PV
        """
        try:
            new_scan_data = await self.spec_tel_obj.scan()
            await self.scan_data.update(new_scan_data)
            if self.capture.get():
                self.file_builder.add_scan(self.scan_data.get())
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from scan trigger attempt: "
                + f"\n{e.args[0]}"
                + "\nScanData PV not updated"
            )

    async def on_capture_change(self, capture: bool):
        if capture:
            self.file_builder.create_file(
                self.nexus_save_file_path.get(), self.nexus_save_file_name.get()
            )
        else:
            self.file_builder.close_file()
