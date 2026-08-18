import asyncio
from unittest.mock import AsyncMock

import pytest
from test_c_common import controller_and_mock_objects

from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError


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

    spec_tel_mock.connect.assert_called()


# Test hidden for now
# Wont work until FastCS created coroutines can be closed manually
# or are closed on connect exceptions
@pytest.mark.asyncio
async def _test_bad_connection(loguru_caplog):
    spec_tel_mock = AsyncMock()

    async def connect():
        raise UnexpectedResponseError

    spec_tel_mock.connect = connect

    (
        task_pointer,
        _,
        spec_tel_mock,
        _,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    task_pointer.cancel()
    await asyncio.gather(task_pointer)

    assert isinstance(error_queue.pop(), UnexpectedResponseError)
