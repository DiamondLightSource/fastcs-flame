import numpy as np
from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String, Waveform
from fastcs.logging import logger
from fastcs.methods.command import command

from fastcsflame.file_builder import FileBuilder
from fastcsflame.flame_controller_attributes import (
    DummyBoolIO,
    DummyBoolIORef,
    DummyStrIO,
    DummyStrIORef,
    IntegrationTimeIO,
    IntegrationTimeIORef,
    SpectrometerScanIO,
    SpectrometerScanIORef,
)
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError


class FlameController(Controller):
    """
    FastCS controller for an OceanOptics Flame spectrometer
    """

    spec_tel_obj: SpecTel
    file_builder: FileBuilder

    integration_time: AttrRW[int, IntegrationTimeIORef]
    # Scan data from spectrometer
    scan_data: AttrR[np.ndarray, SpectrometerScanIORef]

    capture: AttrRW[bool, DummyBoolIORef]
    file_path: AttrRW[str, DummyStrIORef]
    file_name: AttrRW[str, DummyStrIORef]

    def __init__(
        self,
        ip: str,
        port: int,
        mount_path: str = "/",
        default_file_path: str = "dls/b21/data",
        default_file_name: str = "data",
        lowest_wavelength=190,
        highest_wavelength=1100,
        scan_data_length=2044,
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
        super().__init__(
            ios=[
                IntegrationTimeIO(),
                DummyBoolIO(),
                DummyStrIO(),
                SpectrometerScanIO(),
            ]
        )

        self.spec_tel_obj = SpecTel(ip, port)
        self.file_builder = FileBuilder(
            mount_path,
            np.linspace(lowest_wavelength, highest_wavelength, scan_data_length),
        )

        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )
        self.scan_data = AttrR(
            Waveform(int, shape=(scan_data_length,)),
            io_ref=SpectrometerScanIORef(self.spec_tel_obj),
        )

        self.capture = AttrRW(Bool(), io_ref=DummyBoolIORef(False))
        self.capture.add_on_update_callback(self.on_capture_change)
        self.file_path = AttrRW(String(), io_ref=DummyStrIORef(default_file_path))
        self.file_name = AttrRW(String(), io_ref=DummyStrIORef(default_file_name))

    async def connect(self):
        await super().connect()
        await self.spec_tel_obj.connect()

    @command()
    async def single_scan(self):
        """
        Conducts a single scan using the spectrometer
        Stores scan data in ScanData PV and h5 file (if capture mode is on)
        """
        try:
            new_scan_data = await self.spec_tel_obj.scan()
            await self.scan_data.update(new_scan_data)
            if self.capture.get():
                self.file_builder.add_scan(self.scan_data.get())
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from scan trigger attempt: "
                + f"\n{e.args[0] if len(e.args) != 0 else '[No message]'}"
                + "\nScanData PV not updated"
            )

    async def on_capture_change(self, capture: bool):
        """
        Method to run when the value of capture is changed
        Creates a new file to capture scan data in when set to true
        Closes file when set to false
        """
        if capture:
            self.file_builder.create_file(self.file_path.get(), self.file_name.get())
        else:
            self.file_builder.close_file()
