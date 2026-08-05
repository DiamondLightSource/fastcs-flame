from collections.abc import Awaitable, Callable

from fastcs.attributes import AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int
from fastcs.methods.command import command

from fastcsflame.flame_controller_attributes import (
    DummyBoolIO,
    DummyBoolIORef,
    IntegrationTimeIO,
    IntegrationTimeIORef,
)
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


class AdvancedSubcontroller(Controller):
    integration_time: AttrRW[int, IntegrationTimeIORef]
    lamp: AttrRW[bool, DummyBoolIORef]

    def __init__(
        self,
        spec_tel_obj: SpecTel,
        connect_method: Callable[[], Awaitable[None]],
        disconnect_method: Callable[[], Awaitable[None]],
    ):
        super().__init__(ios=[IntegrationTimeIO(), DummyBoolIO()])
        self.connect_method = connect_method
        self.disconnect_method = disconnect_method

        self.spec_tel_obj = spec_tel_obj
        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )
        self.lamp = AttrRW(Bool(), io_ref=DummyBoolIORef(True))
        self.lamp.add_on_update_callback(self.lamp_change)

    async def lamp_change(self, new_lamp_status: bool):
        await self.spec_tel_obj.set_lamp(new_lamp_status)

    @command()
    async def force_connect(self):
        await self.connect_method()

    @command()
    async def force_disconnect(self):
        await self.disconnect_method()
