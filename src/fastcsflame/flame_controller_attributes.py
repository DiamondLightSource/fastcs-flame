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
    """
    Ref for integration time on a FastCS controller
    """

    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=ONCE)

        self.spec_tel_obj = spec_tel_obj


class IntegrationTimeIO(AttributeIO[int, IntegrationTimeIORef]):
    """
    IO for integration time on a FastCS controller
    """

    spec_tel_obj: SpecTel

    def __init__(self):
        super().__init__()

    async def update(self, attr: AttrR[int, IntegrationTimeIORef]):
        """
        Sets the integration time attribute based on the value on the spectrometer
        on controller start up
        This should be called once by FastCS, all future updates should
        be called from send method
        """
        self.spec_tel_obj = attr.io_ref.spec_tel_obj

        try:
            integration_time_value = await self.spec_tel_obj.get_integration_time()

            await attr.update(integration_time_value)
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from integration time query: "
                + f"\n{e.args[0]}"
                + "\nIntegrationTime PV not updated"
            )

    async def send(self, attr: AttrW[int, IntegrationTimeIORef], value: int):
        """
        Updates integration time value on controller
        Calls update method to make sure value was set correct and set read value
        """
        await self.spec_tel_obj.set_integration_time(value)

        # Make sure readback value is inline with what was set
        if isinstance(attr, AttrRW):
            await self.update(attr)


@dataclass
class SpectrometerScanIORef(AttributeIORef):
    """
    Reference for scan attribute on a FastCS controller
    """

    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=ONCE)

        self.spec_tel_obj = spec_tel_obj


class SpectrometerScanIO(AttributeIO[np.ndarray, SpectrometerScanIORef]):
    """
    IO for scan attributes on a FastCS controller
    """

    spec_tel_obj: SpecTel

    def __init__(self):
        super().__init__()

    async def update(self, attr: AttrR[np.ndarray, SpectrometerScanIORef]):
        """
        Sets the scan data attribute based on the last scan the spectrometer took
        on controller start up
        This should be called once. All future updates should be done by
        controller commands
        """
        self.spec_tel_obj = attr.io_ref.spec_tel_obj

        try:
            scan_data = await self.spec_tel_obj.get_last_scan()

            await attr.update(scan_data)
        except UnexpectedResponseError as e:
            logger.warning(
                "Spectrometer gave unexpected response from scan data query: "
                + f"\n{e.args[0]}"
                + "\nScanData PV not updated"
            )


# NOTE: FastCS Float's are not high enough precision to represent all coefficients
# Investigate if this a FastCS issue or an EPICS one
@dataclass
class SpectrommeterWCCIORef(AttributeIORef):
    spec_tel_obj: SpecTel
    order: int

    def __init__(self, spec_tel_obj: SpecTel, order: int):
        super().__init__(update_period=ONCE)

        self.spec_tel_obj = spec_tel_obj
        self.order = order


class SpectrometerWCCIO(AttributeIO[float, SpectrommeterWCCIORef]):
    async def update(self, attr: AttrR[float, SpectrommeterWCCIORef]):
        spec_tel_obj = attr.io_ref.spec_tel_obj

        try:
            scan_data = await spec_tel_obj.get_wcc(attr.io_ref.order)

            await attr.update(scan_data)
        except UnexpectedResponseError as _:
            pass
            # logger.warning(
            #     "Spectrometer gave unexpected response from scan data query: "
            #     + f"\n{e.args[0]}"
            #     + "\nScanData PV not updated"
            # )

    async def send(self, attr: AttrW[float, SpectrommeterWCCIORef], value: float):
        spec_tel_obj = attr.io_ref.spec_tel_obj
        await spec_tel_obj.set_wcc(attr.io_ref.order, value)

        # update RBV to match written value
        if isinstance(attr, AttrRW):
            await attr.update(value)


@dataclass
class LampActiveIORef(AttributeIORef):
    """
    Reference for lamp attribute on a FastCS controller
    """

    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=ONCE)

        self.spec_tel_obj = spec_tel_obj


class LampActiveIO(AttributeIO[bool, LampActiveIORef]):
    """
    IO for lamp attributes on a FastCS controller
    """

    def __init__(self):
        super().__init__()

    async def send(self, attr: AttrW[bool, LampActiveIORef], value: bool):
        """
        Updates lamp active value on controller
        """
        await attr.io_ref.spec_tel_obj.set_lamp(value)
