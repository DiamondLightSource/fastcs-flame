from unittest.mock import AsyncMock

import pytest
from test_c_common import controller_and_mock_objects

from fastcsflame.advanced_subcontroller import AdvancedSubcontroller


@pytest.mark.asyncio
async def test_connection(loguru_caplog):
    """
    Test connect method is called correctly on startup
    """

    (
        _,
        _,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog)

    spec_tel_mock.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_bad_connection(loguru_caplog):
    spec_tel_mock = AsyncMock()

    spec_tel_mock.connect = AsyncMock(side_effect=TimeoutError)

    (
        _,
        _,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    assert "Failed connection attempt" in loguru_caplog.text


@pytest.mark.asyncio
async def test_force_connect(loguru_caplog):
    spec_tel_mock = AsyncMock()

    spec_tel_mock.connect = AsyncMock(side_effect=TimeoutError)

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    spec_tel_mock.connect = AsyncMock()
    advanced_subcontroller = flame_controller.sub_controllers["Advanced"]
    assert isinstance(advanced_subcontroller, AdvancedSubcontroller)
    await advanced_subcontroller.force_connect()

    spec_tel_mock.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_force_disconnect(loguru_caplog):
    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog)

    advanced_subcontroller = flame_controller.sub_controllers["Advanced"]
    assert isinstance(advanced_subcontroller, AdvancedSubcontroller)
    await advanced_subcontroller.force_disconnect()

    spec_tel_mock.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_bad_force_connect(loguru_caplog):
    spec_tel_mock = AsyncMock()

    spec_tel_mock.connect = AsyncMock(side_effect=TimeoutError)

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    loguru_caplog.clear()

    advanced_subcontroller = flame_controller.sub_controllers["Advanced"]
    assert isinstance(advanced_subcontroller, AdvancedSubcontroller)
    await advanced_subcontroller.force_connect()

    assert "Failed connection attempt" in loguru_caplog.text


# TODO: Test connected PV
