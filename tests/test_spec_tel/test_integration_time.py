from unittest.mock import AsyncMock

import pytest
from test_common import start_connection, start_mock_socket

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError

DEFAULT_INTEGRATION_TIME = 10
CHANGED_INTEGRATION_TIME = 8

INTEGRATION_TIME_GET = "?I"
INTEGRATION_TIME_SET = f"I{CHANGED_INTEGRATION_TIME}\n"

DEFAULT_INTEGRATION_TIME_GET_RESPONSE = DummySpectrometer.wrap_response(
    INTEGRATION_TIME_GET, str(DEFAULT_INTEGRATION_TIME)
)
DEFAULT_INTEGRATION_TIME_SET_RESPONSE = DummySpectrometer.wrap_response(
    INTEGRATION_TIME_SET, ""
)


@pytest.mark.asyncio
async def test_get_integration_time_message():
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        # Simulate expected response so no errors are thrown
        # Easier than mocking all the various methods involved
        event_loop.sock_recv = AsyncMock(
            return_value=DEFAULT_INTEGRATION_TIME_GET_RESPONSE
        )
        await spec_tel_obj.get_integration_time()
        socket_obj.send.assert_called_once_with(INTEGRATION_TIME_GET.encode())


@pytest.mark.asyncio
async def test_get_integration_time_decoding():
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        # Simulate expected response so no errors are thrown
        # Easier than mocking all the various methods involved
        event_loop.sock_recv = AsyncMock(
            return_value=DEFAULT_INTEGRATION_TIME_GET_RESPONSE
        )
        recieved_integration_time = await spec_tel_obj.get_integration_time()
        assert recieved_integration_time == DEFAULT_INTEGRATION_TIME


@pytest.mark.asyncio
async def test_get_integration_time():
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        recieved_integration_time = await spec_tel_obj.get_integration_time()
        assert recieved_integration_time == dummy_spec_obj.integration_time


@pytest.mark.asyncio
async def test_get_integration_time_bad_response():
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        dummy_spec_obj.handle_get_integration_time_request = lambda: ""
        with pytest.raises(UnexpectedResponseError):
            await spec_tel_obj.get_integration_time()


@pytest.mark.asyncio
async def test_set_integration_time_message():
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        # Simulate expected response so no errors are thrown
        # Easier than mocking all the various methods involved
        event_loop.sock_recv = AsyncMock(
            return_value=DEFAULT_INTEGRATION_TIME_SET_RESPONSE
        )
        # This also tests the decoding as an error would be raised here if its wrong
        await spec_tel_obj.set_integration_time(CHANGED_INTEGRATION_TIME)
        socket_obj.send.assert_called_once_with(INTEGRATION_TIME_SET.encode())


@pytest.mark.asyncio
async def test_set_integration_time():
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        await spec_tel_obj.set_integration_time(CHANGED_INTEGRATION_TIME)
        assert dummy_spec_obj.integration_time == CHANGED_INTEGRATION_TIME


@pytest.mark.asyncio
async def test_set_integration_time_bad_response(loguru_caplog):
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        dummy_spec_obj.handle_set_integration_time_request = lambda request: ""
        await spec_tel_obj.set_integration_time(CHANGED_INTEGRATION_TIME)
        assert "Negative acknowledgement in response" in loguru_caplog.text
