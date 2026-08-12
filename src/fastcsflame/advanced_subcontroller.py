from collections.abc import Awaitable, Callable

from fastcs.attributes import AttrRW, AttrW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int
from fastcs.methods.command import command

from fastcsflame.flame_controller_attributes import (
    IntegrationTimeIO,
    IntegrationTimeIORef,
    LampActiveIO,
    LampActiveIORef,
)
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


class AdvancedSubcontroller(Controller):
    integration_time: AttrRW[int, IntegrationTimeIORef]
    lamp: AttrW[bool, LampActiveIORef]

    def __init__(
        self,
        spec_tel_obj: SpecTel,
        connect_method: Callable[[], Awaitable[None]],
        disconnect_method: Callable[[], Awaitable[None]],
    ):
        super().__init__(ios=[IntegrationTimeIO(), LampActiveIO()])
        self.connect_method = connect_method
        self.disconnect_method = disconnect_method

        self.spec_tel_obj = spec_tel_obj
        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )
        self.lamp = AttrW(Bool(), io_ref=LampActiveIORef(spec_tel_obj))

    @command()
    async def force_connect(self):
        await self.connect_method()

    @command()
    async def force_disconnect(self):
        await self.disconnect_method()
