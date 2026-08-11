import numpy as np
from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, String, Waveform
from fastcs.logging import logger
from fastcs.methods.command import command

from fastcsflame.advanced_subcontroller import AdvancedSubcontroller
from fastcsflame.calibration_subcontroller import CalibrationSubcontroller
from fastcsflame.file_builder import FileBuilder
from fastcsflame.flame_controller_attributes import (
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
    connected: AttrR[bool]
    # Scan data from spectrometer
    scan_data: AttrR[np.ndarray, SpectrometerScanIORef]

    capture: AttrRW[bool]
    # Where h5 files will be saved within the mounted directory
    file_path: AttrRW[str]
    # Name of saved h5 file (not including extension)
    file_name: AttrRW[str]

    scan_in_progress: AttrR[bool]

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
        mount_path: Path to mounted DLS filesystem directory in container
        default_file_path: Initial value for file_path PV
        defualt_file_name: Initial value for file_name PV
        lowest_wavelength: Lowest wavelength spectrometer can measure (in nm)
        highest_wavelength: Highest wavelength spectrometer can measure (in nm)
        scan_data_length: Number of discrete intensity values included returned
            from a spectrometer scan
        """
        super().__init__(
            ios=[
                SpectrometerScanIO(),
            ]
        )

        self.connected = AttrR(Bool())

        self.spec_tel_obj = SpecTel(ip, port)
        self.file_builder = FileBuilder(
            mount_path,
            np.linspace(lowest_wavelength, highest_wavelength, scan_data_length),
        )

        self.scan_data = AttrR(
            Waveform(int, shape=(scan_data_length,)),
            io_ref=SpectrometerScanIORef(self.spec_tel_obj),
        )

        self.capture = AttrRW(Bool(), initial_value=False)
        self.capture.add_on_update_callback(self.on_capture_change)
        self.file_path = AttrRW(String(), initial_value=default_file_path)
        self.file_name = AttrRW(String(), initial_value=default_file_name)

        self.scan_in_progress = AttrR(Bool(), initial_value=False)

        self.add_sub_controller(
            "Advanced",
            AdvancedSubcontroller(self.spec_tel_obj, self.connect, self.disconnect),
        )
        self.add_sub_controller(
            "Calibration", CalibrationSubcontroller(self.spec_tel_obj)
        )

    async def connect(self):
        await super().connect()
        try:
            await self.spec_tel_obj.connect()
        # May cause issues if spec_tel_obj is updated separately from this object
        # Shouldnt happen due to compositional relationship
        except BaseException as e:
            logger.warning("Failed connection attempt")
            logger.warning(e)
        await self.connected.update(self.spec_tel_obj.connected)

    async def disconnect(self) -> None:
        await super().disconnect()
        await self.spec_tel_obj.disconnect()
        await self.connected.update(self.spec_tel_obj.connected)

    @command()
    async def single_scan(self):
        """
        Conducts a single scan using the spectrometer
        Stores scan data in ScanData PV and h5 file (if capture mode is on)
        """
        try:
            await self.scan_in_progress.update(True)
            new_scan_data = await self.spec_tel_obj.scan()
            await self.scan_in_progress.update(False)
            await self.scan_data.update(new_scan_data)
            if self.capture.get():
                self.file_builder.add_scan(self.scan_data.get())
        except UnexpectedResponseError as e:
            await self.scan_in_progress.update(False)
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
