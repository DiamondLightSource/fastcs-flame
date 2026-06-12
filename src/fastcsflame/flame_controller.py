from dataclasses import dataclass

from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW, AttrW
from fastcs.controllers import Controller
from fastcs.datatypes import Int
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


class FlameController(Controller):
    spec_tel_obj: SpecTel

    integration_time: AttrRW

    def __init__(self, ip: str, port: int):
        super().__init__(ios=[IntegrationTimeIO()])

        self.spec_tel_obj = SpecTel(ip, port)

        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )

    async def connect(self):
        await super().connect()
        self.spec_tel_obj.connect()
