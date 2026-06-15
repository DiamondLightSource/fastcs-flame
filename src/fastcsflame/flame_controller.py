from dataclasses import dataclass

import numpy as np
from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW, AttrW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, Waveform
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


class ScanTriggerIORef(AttributeIORef):
    def __init__(self):
        super().__init__(update_period=None)


class ScanTriggerIO(AttributeIO[bool, ScanTriggerIORef]):
    spec_tel_obj: SpecTel

    def __init__(
        self,
        scan_data_attribte: AttrR[np.ndarray, ScanDataIORef],
        spec_tel_obj: SpecTel,
    ):
        self.spec_tel_obj = spec_tel_obj
        self.scan_data_attribute = scan_data_attribte

    async def send(self, attr: AttrW[bool, ScanTriggerIORef], value: bool):
        if not value:
            # Input false?
            # Why even bother?
            return

        new_scan_data = self.spec_tel_obj.scan()
        await self.scan_data_attribute.update(new_scan_data)
        # Set the value back to False here??
        # How do I do this in FastCS? I see no method


class FlameController(Controller):
    spec_tel_obj: SpecTel

    integration_time: AttrRW[int, IntegrationTimeIORef] = AttrRW(
        Int(), io_ref=IntegrationTimeIORef()
    )
    scan_data: AttrR[np.ndarray, ScanDataIORef] = AttrR(
        Waveform(int, shape=(2048,)), io_ref=ScanDataIORef()
    )
    trigger_scan: AttrW[bool, ScanTriggerIORef] = AttrW(
        Bool(), io_ref=ScanTriggerIORef()
    )

    def __init__(self, ip: str, port: int):
        self.spec_tel_obj = SpecTel(ip, port)

        super().__init__(
            ios=[
                IntegrationTimeIO(self.spec_tel_obj),
                ScanDataIO(self.spec_tel_obj),
                ScanTriggerIO(self.scan_data, self.spec_tel_obj),
            ]
        )

    async def connect(self):
        await super().connect()
        self.spec_tel_obj.connect()
