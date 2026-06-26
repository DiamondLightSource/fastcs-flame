import asyncio
from datetime import datetime, timedelta

import numpy as np
from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Int, String, Waveform
from fastcs.logging import logger
from fastcs.methods.command import command
from numpy.typing import NDArray

from fastcsflame.flame_controller_attributes import (
    DummyIntIO,
    DummyIntIORef,
    DummyStrIO,
    DummyStrIORef,
    IntegrationTimeIORef,
    ScanDataIORef,
    SpectrometerIntIO,
    SpectrometerScanIO,
)
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
    output_data_file_path: str

    integration_time: AttrRW[int, IntegrationTimeIORef]

    # Time to acquire data over
    # NOT a value from the spectrometer
    acquisition_period: AttrRW[int, DummyIntIORef]

    # Number of scans to perform in acquisition period
    # NOT a value from the spectrometer
    total_scans: AttrRW[int, DummyIntIORef]

    nexus_save_file_path: AttrRW[str, DummyStrIORef]
    nexus_save_file_name: AttrRW[str, DummyStrIORef]

    # Scan data from spectrometer
    scan_data: AttrR[np.ndarray, ScanDataIORef]

    def __init__(
        self,
        ip: str,
        port: int,
        output_data_file_path: str = "",
        default_acquisition_period: int = 45,
        default_total_scans: int = 3,
        default_nexus_save_file_path: str = "./",
        default_nexus_save_file_name: str = "data.nxs",
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
        self.output_data_file_path = output_data_file_path

        super().__init__(
            ios=[
                SpectrometerIntIO(),
                DummyIntIO(),
                DummyStrIO(),
                SpectrometerScanIO(),
            ]
        )

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

        self.scan_data = AttrR(
            Waveform(int, shape=(SCAN_DATA_LENGTH,)),
            io_ref=ScanDataIORef(self.spec_tel_obj),
        )

    async def connect(self):
        await super().connect()
        self.spec_tel_obj.connect()

    @command()
    async def single_scan(self):
        """
        Conducts a single scan using the spectrometer
        Stores scan data in ScanData PV
        """
        try:
            new_scan_data = self.spec_tel_obj.scan()
            await self.scan_data.update(new_scan_data)
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from scan trigger attempt: "
                + f"\n{e.args[0]}"
                + "\nScanData PV not updated"
            )

    @command()
    async def acquire_data(self):
        """
        Starts the data acquisition process
        Conducts [TotalScans] scans over a period of [AcquisitionPeriod] seconds
        Scans are evenly spaced with one conducted when the command is called
        and one conducted [AcquisitionPeriod] seconds after the command is called
        It takes roughly 11 seconds to send scan data so if TotalScans is set too high
        for the AcquisitionPeriod scans will be conducted behind schedule
        In this case a warning is logged
        Data is output to output_data_filepath
        """
        start_time = datetime.now()

        acquisition_period = self.acquisition_period.get()
        total_scans = self.total_scans.get()

        schedule: list[datetime] = [
            start_time + timedelta(seconds=n * acquisition_period / (total_scans - 1))
            for n in range(total_scans)
        ]

        actual_scan_times: list[datetime] = []
        scan_data: list[NDArray] = []

        for scheduled_time in schedule:
            loop_start_time = datetime.now()

            # wait until scheduled time for scan
            if loop_start_time < scheduled_time:
                await asyncio.sleep((scheduled_time - loop_start_time).total_seconds())
            else:
                logger.warning(
                    "Scan is behind schedule\n"
                    + f"Time: {loop_start_time}\n"
                    + f"Expected scan start time: {scheduled_time}\n"
                    + "This is likely because too many scans are requested in the "
                    + "acquisition period. It takes roughly 11 seconds to send data "
                    + "from a scan, consider decreasing TotalScans value"
                )

            scan_start_time = datetime.now()
            await self.single_scan()

            # Better to make this one list of tuples??
            actual_scan_times.append(scan_start_time)
            scan_data.append(self.scan_data.get())

        self._write_scan_data_to_file(scan_data, actual_scan_times)

    def _write_scan_data_to_file(
        self, scan_data: list[NDArray], scan_times: list[datetime]
    ):
        """
        Writes data from a data acquisition process to the output file
        scan_data: A list of 1D numpy arrays of integers
            Each array contains data from one scan
        scan_times: A list of datetimes that scans were conducted
            This list should be the same length as the scan_data list
        For each scan, writes the datetime with hashes either side
        then writes raw scan data on a new line. Values are separated by commas
        """
        if self.output_data_file_path == "":
            return

        with open(self.output_data_file_path, "x") as file:
            for i in range(len(scan_data)):
                file.write("#" + str(scan_times[i]) + "#\n")
                for value in scan_data[i]:
                    file.write(str(value) + ",")
                file.write("\n")
