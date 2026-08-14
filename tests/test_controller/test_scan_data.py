import asyncio
from unittest.mock import AsyncMock

import numpy as np
import pytest
from test_common import controller_and_mock_objects

from common import lists_equal
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError

INITIAL_DUMMY_SCAN_DATA = np.array(range(10))
SET_DUMMY_SCAN_DATA = np.array(range(10)) + 10


@pytest.mark.asyncio
async def test_initialisation(loguru_caplog):
    spec_tel_mock = AsyncMock()
    spec_tel_mock.last_scan_data = INITIAL_DUMMY_SCAN_DATA

    async def get_last_scan():
        return spec_tel_mock.last_scan_data

    spec_tel_mock.get_last_scan = get_last_scan

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    # Make sure initial scan data matches spec tel object
    assert lists_equal(flame_controller.scan_data.get(), spec_tel_mock.last_scan_data)


@pytest.mark.asyncio
async def test_scan_data_command(loguru_caplog):
    spec_tel_mock = AsyncMock()
    spec_tel_mock.last_scan_data = INITIAL_DUMMY_SCAN_DATA

    async def get_last_scan():
        return spec_tel_mock.last_scan_data

    async def scan():
        spec_tel_mock.last_scan_data = SET_DUMMY_SCAN_DATA
        return spec_tel_mock.last_scan_data

    spec_tel_mock.get_last_scan = get_last_scan
    spec_tel_mock.scan = scan

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    old_scan_data = flame_controller.scan_data.get()
    await flame_controller.single_scan()
    new_scan_data = flame_controller.scan_data.get()

    # Make sure scan data has changed
    assert not lists_equal(old_scan_data, new_scan_data)
    # Make sure new scan data matches spec tel object
    assert lists_equal(new_scan_data, spec_tel_mock.last_scan_data)


# Test hidden for now
# Wont work until FastCS created coroutines can be closed manually
# or are closed on connect exceptions
@pytest.mark.asyncio
async def _test_bad_last_scan_data_get(loguru_caplog):
    spec_tel_mock = AsyncMock()

    async def get_last_scan():
        raise UnexpectedResponseError

    spec_tel_mock.get_integration_time = get_last_scan

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
async def test_bad_scan_command(loguru_caplog):
    spec_tel_mock = AsyncMock()

    spec_tel_mock.last_scan_data = INITIAL_DUMMY_SCAN_DATA

    async def get_scan_data():
        return spec_tel_mock.last_scan_data

    def scan():
        raise UnexpectedResponseError

    spec_tel_mock.get_scan_data = get_scan_data
    spec_tel_mock.scan = scan

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await flame_controller.single_scan()

    assert (
        "Spectrometer gave unexpected response from scan trigger attempt: "
        in loguru_caplog.text
    )
