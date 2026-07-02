import numpy as np
from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String, Waveform
from fastcs.logging import logger
from fastcs.methods.command import command

from fastcsflame.flame_controller_attributes import (
    DummyBoolIO,
    DummyBoolIORef,
    DummyIntIO,
    DummyIntIORef,
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

# Should be 2048 in theory but 2044 in practice
SCAN_DATA_LENGTH = 2044


class FlameController(Controller):
    """
    FastCS controller for an OceanOptics Flame spectrometer
    """

    spec_tel_obj: SpecTel

    integration_time: AttrRW[int, IntegrationTimeIORef]

    # Time to acquire data over
    # NOT a value from the spectrometer
    acquisition_period: AttrRW[int, DummyIntIORef]

    # Number of scans to perform in acquisition period
    # NOT a value from the spectrometer
    total_scans: AttrRW[int, DummyIntIORef]

    nexus_save_file_path: AttrRW[str, DummyStrIORef]
    nexus_save_file_name: AttrRW[str, DummyStrIORef]
    title: AttrRW[str, DummyStrIORef]
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
        default_acquisition_period: int = 45,
        default_total_scans: int = 3,
        default_nexus_save_file_path: str = "./",
        default_nexus_save_file_name: str = "data.nxs",
        default_title: str = "Experiment Title",
        default_sample_name: str = "Sample Name",
        default_sample_id: str = "SampleID",
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
                DummyIntIO(),
                DummyStrIO(),
                SpectrometerScanIO(),
            ]
        )

        self.file_builder = Hdf5FileBuilder()

        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )

        self.acquisition_period = AttrRW(
            Int(), io_ref=DummyIntIORef(default_acquisition_period)
        )

        self.total_scans = AttrRW(Int(), io_ref=DummyIntIORef(default_total_scans))

        self.nexus_save_file_path = AttrRW(
            String(), io_ref=DummyStrIORef(default_nexus_save_file_path)
        )
        self.nexus_save_file_name = AttrRW(
            String(), io_ref=DummyStrIORef(default_nexus_save_file_name)
        )
        self.title = AttrRW(String(), io_ref=DummyStrIORef(default_title))
        self.sample_name = AttrRW(String(), io_ref=DummyStrIORef(default_sample_name))
        self.sample_id = AttrRW(String(), io_ref=DummyStrIORef(default_sample_id))
        self.capture = AttrRW(Bool(), io_ref=DummyBoolIORef(False))

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
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from scan trigger attempt: "
                + f"\n{e.args[0]}"
                + "\nScanData PV not updated"
            )
