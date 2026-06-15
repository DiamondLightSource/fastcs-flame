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
    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=ONCE)
        self.spec_tel_obj = spec_tel_obj


class IntegrationTimeIO(AttributeIO[int, IntegrationTimeIORef]):
    def __init__(self):
        super().__init__()

    async def update(self, attr: AttrR[int, IntegrationTimeIORef]):
        integration_time_value = attr.io_ref.spec_tel_obj.get_integration_time()

        await attr.update(integration_time_value)

    async def send(self, attr: AttrW[int, IntegrationTimeIORef], value: int):
        attr.io_ref.spec_tel_obj.set_integration_time(value)


class ScanDataIORef(AttributeIORef):
    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=ONCE)
        self.spec_tel_obj = spec_tel_obj


class ScanDataIO(AttributeIO[np.ndarray, ScanDataIORef]):
    async def update(self, attr: AttrR[np.ndarray, ScanDataIORef]):
        scan_data = attr.io_ref.spec_tel_obj.get_last_scan()

        await attr.update(scan_data)


class ScanTriggerIORef(AttributeIORef):
    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=None)
        self.spec_tel_obj = spec_tel_obj


class ScanTriggerIO(AttributeIO[bool, ScanTriggerIORef]):
    def __init__(self, scan_data_attribte: AttrR[np.ndarray, ScanDataIORef]):
        self.scan_data_attribute = scan_data_attribte

    async def send(self, attr: AttrW[bool, ScanTriggerIORef], value: bool):
        if not value:
            # Input false?
            # Why even bother?
            return

        new_scan_data = attr.io_ref.spec_tel_obj.scan()
        await self.scan_data_attribute.update(new_scan_data)
        # Set the value back to False here??
        # How do I do this in FastCS? I see no method


class FlameController(Controller):
    spec_tel_obj: SpecTel

    integration_time: AttrRW[int, IntegrationTimeIORef]
    scan_data: AttrR[np.ndarray, ScanDataIORef]
    trigger_scan: AttrW[bool, ScanTriggerIORef]

    def __init__(self, ip: str, port: int):
        super().__init__(
            ios=[IntegrationTimeIO(), ScanDataIO(), ScanTriggerIO(self.scan_data)]
        )

        self.spec_tel_obj = SpecTel(ip, port)

        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )
        self.scan_data = AttrR(
            Waveform(int, shape=(2048,)), io_ref=ScanDataIORef(self.spec_tel_obj)
        )

        self.trigger_scan = AttrW(Bool(), io_ref=ScanTriggerIORef(self.spec_tel_obj))

    async def connect(self):
        await super().connect()
        self.spec_tel_obj.connect()
