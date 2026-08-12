import asyncio
from unittest.mock import AsyncMock

import pytest
from test_common import controller_and_mock_objects

from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError

INITIAL_DUMMY_INTEGRATION_TIME = 10
SET_DUMMY_INTEGRATION_TIME = 8


@pytest.mark.asyncio
async def test_initialisation(loguru_caplog):
    spec_tel_mock = AsyncMock()
    spec_tel_mock.integration_time = INITIAL_DUMMY_INTEGRATION_TIME

    async def get_integration_time():
        return spec_tel_mock.integration_time

    spec_tel_mock.get_integration_time = get_integration_time

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    # Make sure initial integration time matches spec tel object
    assert flame_controller.integration_time.get() == spec_tel_mock.integration_time


@pytest.mark.asyncio
async def test_set_integration_time(loguru_caplog):

    spec_tel_mock = AsyncMock()
    spec_tel_mock.integration_time = INITIAL_DUMMY_INTEGRATION_TIME

    async def get_integration_time():
        return spec_tel_mock.integration_time

    def set_integration_time(integration_time: int):
        spec_tel_mock.integration_time = integration_time

    spec_tel_mock.get_integration_time = get_integration_time
    spec_tel_mock.set_integration_time = set_integration_time

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await flame_controller.integration_time.put(SET_DUMMY_INTEGRATION_TIME)
    # Make sure new integration time matches spec tel object
    assert spec_tel_mock.integration_time == SET_DUMMY_INTEGRATION_TIME


# Test hidden for now
# Wont work until FastCS created coroutines can be closed manually
# or are closed on connect exceptions
@pytest.mark.asyncio
async def _test_bad_integration_time_get(loguru_caplog):
    spec_tel_mock = AsyncMock()

    async def get_integration_time():
        raise UnexpectedResponseError

    spec_tel_mock.get_integration_time = get_integration_time

    (
        task_pointer,
        _,
        spec_tel_mock,
        _,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await asyncio.gather(task_pointer)

    assert isinstance(error_queue.pop(), UnexpectedResponseError)


@pytest.mark.asyncio
async def test_bad_integration_time_set(loguru_caplog):
    spec_tel_mock = AsyncMock()

    spec_tel_mock.integration_time = INITIAL_DUMMY_INTEGRATION_TIME

    async def get_integration_time():
        return spec_tel_mock.integration_time

    def set_integration_time(integration_time: int):
        raise UnexpectedResponseError

    spec_tel_mock.get_integration_time = get_integration_time
    spec_tel_mock.set_integration_time = set_integration_time

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await flame_controller.integration_time.put(SET_DUMMY_INTEGRATION_TIME)

    assert "UnexpectedResponseError" in loguru_caplog.text
