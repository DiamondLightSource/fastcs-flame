import asyncio
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW, AttrW
from fastcs.controllers import Controller
from fastcs.datatypes import Int, Waveform
from fastcs.methods.command import command
from fastcs.util import ONCE

from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


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
        integration_time_value = self.spec_tel_obj.get_integration_time()

        await attr.update(integration_time_value)

    async def send(self, attr: AttrW[int, IntegrationTimeIORef], value: int):
        self.spec_tel_obj.set_integration_time(value)


class ScanDataIORef(AttributeIORef):
    def __init__(self):
        super().__init__(update_period=ONCE)


class ScanDataIO(AttributeIO[np.ndarray, ScanDataIORef]):
    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__()

        self.spec_tel_obj = spec_tel_obj

    async def update(self, attr: AttrR[np.ndarray, ScanDataIORef]):
        scan_data = self.spec_tel_obj.get_last_scan()

        await attr.update(scan_data)


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
        return


class TotalImagesIORef(AttributeIORef):
    def __init__(self):
        super().__init__(update_period=ONCE)


class TotalImagesIO(AttributeIO[int, TotalImagesIORef]):
    initial_value: int

    def __init__(self, initial_value: int):
        self.initial_value = initial_value

    async def update(self, attr: AttrR[int, TotalImagesIORef]):

        await attr.update(self.initial_value)

    async def send(self, attr: AttrW[int, TotalImagesIORef], value: int):
        return


class FlameController(Controller):
    spec_tel_obj: SpecTel

    integration_time: AttrRW[int, IntegrationTimeIORef] = AttrRW(
        Int(), io_ref=IntegrationTimeIORef()
    )

    acquisition_period: AttrRW[int, AcquisitionPeriodIORef] = AttrRW(
        Int(), io_ref=AcquisitionPeriodIORef()
    )

    total_images: AttrRW[int, TotalImagesIORef] = AttrRW(
        Int(), io_ref=TotalImagesIORef()
    )

    scan_data: AttrR[np.ndarray, ScanDataIORef] = AttrR(
        Waveform(int, shape=(2048,)), io_ref=ScanDataIORef()
    )

    def __init__(self, ip: str, port: int):
        self.spec_tel_obj = SpecTel(ip, port)

        super().__init__(
            ios=[
                IntegrationTimeIO(self.spec_tel_obj),
                AcquisitionPeriodIO(15),
                TotalImagesIO(3),
                ScanDataIO(self.spec_tel_obj),
            ]
        )

    async def connect(self):
        await super().connect()
        self.spec_tel_obj.connect()

    @command()
    async def single_scan(self):
        new_scan_data = self.spec_tel_obj.scan()
        await self.scan_data.update(new_scan_data)

    @command()
    async def acquire_data(self):
        start_time = datetime.now()

        acquisition_period = self.acquisition_period.get()
        total_images = self.total_images.get()
        period = acquisition_period / total_images

        for _ in range(total_images):
            print(f"start time: {start_time}")
            await self.single_scan()
            # TODO: Send / store scan data here
            print(self.scan_data.get())

            post_scan_time = datetime.now()
            print(f"post scan time: {post_scan_time}")
            scan_time_delta = post_scan_time - start_time
            scan_time_delta_us = (
                scan_time_delta.total_seconds() * 1000000
            ) + scan_time_delta.microseconds
            wait_time = period - (scan_time_delta_us / 1000000)

            await asyncio.sleep(wait_time)
            start_time = datetime.now()
