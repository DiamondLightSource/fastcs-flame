from fastcs.attributes import AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int

from fastcsflame.flame_controller_attributes import (
    DummyBoolIO,
    DummyBoolIORef,
    IntegrationTimeIO,
    IntegrationTimeIORef,
)


class FlameController(Controller):
    integration_time: AttrRW[int, IntegrationTimeIORef]
    lamp: AttrRW[bool, DummyBoolIORef]

    def __init__(self, spec_tel_obj):
        super().__init__(ios=[IntegrationTimeIO(), DummyBoolIO()])

        self.spec_tel_obj = spec_tel_obj
        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )
        self.lamp = AttrRW(Bool(), io_ref=DummyBoolIORef(True))
        self.lamp.add_on_update_callback(self.lamp_change)

    async def lamp_change(self, new_lamp_status):
        pass
