import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW, AttrW
from fastcs.controllers import Controller
from fastcs.datatypes import Int, Waveform
from fastcs.logging import logger
from fastcs.methods.command import command
from fastcs.util import ONCE
from numpy.typing import NDArray

from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError


@dataclass
class IntegrationTimeIORef(AttributeIORef):
    def __init__(self):
        super().__init__(update_period=ONCE)


class IntegrationTimeIO(AttributeIO[int, IntegrationTimeIORef]):
    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__()

        self.spec_tel_obj = spec_tel_obj

    async def update(self, attr: AttrR[int, IntegrationTimeIORef]):

        try:
            integration_time_value = self.spec_tel_obj.get_integration_time()

            await attr.update(integration_time_value)
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from integration time query: "
                + f"\n{e.args[0]}"
                + "\nIntegrationTime PV not updated"
            )

    async def send(self, attr: AttrW[int, IntegrationTimeIORef], value: int):
        self.spec_tel_obj.set_integration_time(value)

        # Make sure readback value is inline with what was set
        if isinstance(attr, AttrRW):
            await self.update(attr)


class ScanDataIORef(AttributeIORef):
    def __init__(self):
        super().__init__(update_period=ONCE)


class ScanDataIO(AttributeIO[np.ndarray, ScanDataIORef]):
    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__()

        self.spec_tel_obj = spec_tel_obj

    async def update(self, attr: AttrR[np.ndarray, ScanDataIORef]):
        try:
            scan_data = self.spec_tel_obj.get_last_scan()

            await attr.update(scan_data)
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from scan data query: "
                + f"\n{e.args[0]}"
                + "\nScanData PV not updated"
            )


class AcquisitionPeriodIORef(AttributeIORef):
    def __init__(self):
        super().__init__(update_period=ONCE)


class AcquisitionPeriodIO(AttributeIO[int, AcquisitionPeriodIORef]):
    initial_value: int

    def __init__(self, initial_value: int):
        self.initial_value = initial_value

    async def update(self, attr: AttrR[int, AcquisitionPeriodIORef]):

        await attr.update(self.initial_value)

    async def send(self, attr: AttrW[int, AcquisitionPeriodIORef], value: int):

        # update RBV to match written value
        if isinstance(attr, AttrRW):
            await attr.update(value)


class TotalScansIORef(AttributeIORef):
    def __init__(self):
        super().__init__(update_period=ONCE)


class TotalScansIO(AttributeIO[int, TotalScansIORef]):
    initial_value: int

    def __init__(self, initial_value: int):
        self.initial_value = initial_value

    async def update(self, attr: AttrR[int, TotalScansIORef]):

        await attr.update(self.initial_value)

    async def send(self, attr: AttrW[int, TotalScansIORef], value: int):

        # update RBV to match written value
        if isinstance(attr, AttrRW):
            await attr.update(value)


class FlameController(Controller):
    spec_tel_obj: SpecTel
    output_data_file_path: str

    integration_time: AttrRW[int, IntegrationTimeIORef] = AttrRW(
        Int(), io_ref=IntegrationTimeIORef()
    )

    acquisition_period: AttrRW[int, AcquisitionPeriodIORef] = AttrRW(
        Int(), io_ref=AcquisitionPeriodIORef()
    )

    total_scans: AttrRW[int, TotalScansIORef] = AttrRW(Int(), io_ref=TotalScansIORef())

    scan_data: AttrR[np.ndarray, ScanDataIORef] = AttrR(
        Waveform(int, shape=(2048,)), io_ref=ScanDataIORef()
    )

    def __init__(self, ip: str, port: int, output_data_file_path: str = ""):
        self.spec_tel_obj = SpecTel(ip, port)
        self.output_data_file_path = output_data_file_path

        super().__init__(
            ios=[
                IntegrationTimeIO(self.spec_tel_obj),
                AcquisitionPeriodIO(45),
                TotalScansIO(3),
                ScanDataIO(self.spec_tel_obj),
            ]
        )

    async def connect(self):
        await super().connect()
        self.spec_tel_obj.connect()

    @command()
    async def single_scan(self):
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
        if self.output_data_file_path == "":
            return

        with open(self.output_data_file_path, "x") as file:
            for i in range(len(scan_data)):
                file.write("#" + str(scan_times[i]) + "#\n")
                for value in scan_data[i]:
                    file.write(str(value) + ",")
                file.write("\n")
