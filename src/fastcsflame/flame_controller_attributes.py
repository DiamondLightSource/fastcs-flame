from dataclasses import dataclass

import numpy as np
from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW, AttrW
from fastcs.logging import logger
from fastcs.util import ONCE

from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError


@dataclass
class IntegrationTimeIORef(AttributeIORef):
    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=ONCE)

        self.spec_tel_obj = spec_tel_obj


class SpectrometerIntIO(AttributeIO[int, IntegrationTimeIORef]):
    spec_tel_obj: SpecTel

    def __init__(self):
        super().__init__()

    async def update(self, attr: AttrR[int, IntegrationTimeIORef]):
        self.spec_tel_obj = attr.io_ref.spec_tel_obj

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


@dataclass
class ScanDataIORef(AttributeIORef):
    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=ONCE)

        self.spec_tel_obj = spec_tel_obj


class SpectrometerScanIO(AttributeIO[np.ndarray, ScanDataIORef]):
    spec_tel_obj: SpecTel

    def __init__(self):
        super().__init__()

    async def update(self, attr: AttrR[np.ndarray, ScanDataIORef]):
        self.spec_tel_obj = attr.io_ref.spec_tel_obj

        try:
            scan_data = self.spec_tel_obj.get_last_scan()

            await attr.update(scan_data)
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from scan data query: "
                + f"\n{e.args[0]}"
                + "\nScanData PV not updated"
            )


@dataclass
class DummyIntIORef(AttributeIORef):
    default_value: int

    def __init__(self, default_value: int):
        super().__init__(update_period=ONCE)
        self.default_value = default_value


class DummyIntIO(AttributeIO[int, DummyIntIORef]):
    async def update(self, attr: AttrR[int, DummyIntIORef]):

        await attr.update(attr.io_ref.default_value)

    async def send(self, attr: AttrW[int, DummyIntIORef], value: int):

        # update RBV to match written value
        if isinstance(attr, AttrRW):
            await attr.update(value)
