from unittest.mock import AsyncMock

import pytest
from test_c_common import controller_and_mock_objects

from fastcsflame.advanced_subcontroller import AdvancedSubcontroller
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError


@pytest.mark.asyncio
async def test_set_lamp(loguru_caplog):
    """
    Test setting the lamp PV
    """

    spec_tel_mock = AsyncMock()

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    advanced_subcontroller = flame_controller.sub_controllers["Advanced"]
    assert isinstance(advanced_subcontroller, AdvancedSubcontroller)
    await advanced_subcontroller.lamp.put(True)
    spec_tel_mock.set_lamp.assert_awaited_once_with(True)


@pytest.mark.asyncio
async def test_bad_set_lamp(loguru_caplog):
    """
    Test raising an error from the set lamp method
    """
    spec_tel_mock = AsyncMock()

    spec_tel_mock.set_lamp = AsyncMock(side_effect=UnexpectedResponseError)

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    advanced_subcontroller = flame_controller.sub_controllers["Advanced"]
    assert isinstance(advanced_subcontroller, AdvancedSubcontroller)
    await advanced_subcontroller.lamp.put(True)

    assert "UnexpectedResponseError" in loguru_caplog.text
