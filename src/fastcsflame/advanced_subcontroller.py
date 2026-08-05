from fastcs.attributes import AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Int

from fastcsflame.flame_controller_attributes import (
    IntegrationTimeIO,
    IntegrationTimeIORef,
)


class FlameController(Controller):
    integration_time: AttrRW[int, IntegrationTimeIORef]

    def __init__(self, spec_tel_obj):
        super().__init__(
            ios=[
                IntegrationTimeIO(),
            ]
        )

        self.spec_tel_obj = spec_tel_obj
        self.integration_time = AttrRW(
            Int(), io_ref=IntegrationTimeIORef(self.spec_tel_obj)
        )
