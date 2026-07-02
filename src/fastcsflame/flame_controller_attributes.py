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


class SpectrometerIntIO(AttributeIO[int, IntegrationTimeIORef]):
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
class ScanDataIORef(AttributeIORef):
    """
    Reference for scan attribute on a FastCS controller
    """

    spec_tel_obj: SpecTel

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(update_period=ONCE)

        self.spec_tel_obj = spec_tel_obj


class SpectrometerScanIO(AttributeIO[np.ndarray, ScanDataIORef]):
    """
    IO for scan attributes on a FastCS controller
    """

    spec_tel_obj: SpecTel

    def __init__(self):
        super().__init__()

    async def update(self, attr: AttrR[np.ndarray, ScanDataIORef]):
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


@dataclass
class DummyBoolIORef(AttributeIORef):
    """
    Reference for a int attribute on a FastCS controller that
    is not a property of the device
    """

    default_value: bool

    def __init__(self, default_value: bool):
        super().__init__(update_period=ONCE)
        self.default_value = default_value


class DummyBoolIO(AttributeIO[bool, DummyBoolIORef]):
    """
    IO for integer attribtues on a FastCS controller that are
    not properties of the device
    """

    async def update(self, attr: AttrR[bool, DummyBoolIORef]):
        """
        Sets the default value for the attribute
        SHOULD ONLY BE CALLED ONCE (Ref should habe update_period=ONCE)
        """

        await attr.update(attr.io_ref.default_value)

    async def send(self, attr: AttrW[bool, DummyBoolIORef], value: bool):

        # update RBV to match written value
        if isinstance(attr, AttrRW):
            await attr.update(value)


# Could this and DummyIntIORef be 1 generic class??
# Or would this break fastcs??
@dataclass
class DummyStrIORef(AttributeIORef):
    """
    Reference for a string attribute on a FastCS controller that
    is not a property of the device
    """

    default_value: str

    def __init__(self, default_value: str):
        super().__init__(update_period=ONCE)
        self.default_value = default_value


class DummyStrIO(AttributeIO[str, DummyStrIORef]):
    """
    IO for string attribtues on a FastCS controller that are
    not properties of the device
    """

    async def update(self, attr: AttrR[str, DummyStrIORef]):
        """
        Sets the default value for the attribute
        SHOULD ONLY BE CALLED ONCE (Ref should habe update_period=ONCE)
        """

        await attr.update(attr.io_ref.default_value)

    async def send(self, attr: AttrW[str, DummyStrIORef], value: str):

        # update RBV to match written value
        if isinstance(attr, AttrRW):
            await attr.update(value)
