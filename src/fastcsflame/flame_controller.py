from dataclasses import dataclass

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


class FlameController(Controller):
    spec_tel_obj: SpecTel

    integration_time: AttrRW[int, IntegrationTimeIORef] = AttrRW(
        Int(), io_ref=IntegrationTimeIORef()
    )
    scan_data: AttrR[np.ndarray, ScanDataIORef] = AttrR(
        Waveform(int, shape=(2048,)), io_ref=ScanDataIORef()
    )

    def __init__(self, ip: str, port: int):
        self.spec_tel_obj = SpecTel(ip, port)

        super().__init__(
            ios=[
                IntegrationTimeIO(self.spec_tel_obj),
                ScanDataIO(self.spec_tel_obj),
            ]
        )

    async def connect(self):
        await super().connect()
        self.spec_tel_obj.connect()

    @command()
    async def scan(self):
        new_scan_data = self.spec_tel_obj.scan()
        await self.scan_data.update(new_scan_data)
