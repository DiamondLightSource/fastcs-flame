from unittest.mock import AsyncMock

import pytest
from test_st_common import start_connection, start_mock_socket

from dummy_spectrometer import DummySpectrometer

CHANGED_LAMP_BOOL = True
CHANGED_LAMP_INT = 1
LAMP_SET = f"J{CHANGED_LAMP_INT}\n"

DEFAULT_LAMP_SET_RESPONSE = DummySpectrometer.wrap_response(LAMP_SET, "")

# Get lamp request on real spectrometer does not work so it has not been implemented


@pytest.mark.asyncio
async def test_set_lamp_message():
    """
    Test the message sent when set_lamp() is called
    """
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        # Simulate expected response so no errors are thrown
        # Easier than mocking all the various methods involved
        event_loop.sock_recv = AsyncMock(return_value=DEFAULT_LAMP_SET_RESPONSE)
        # This also tests the decoding as an error would be raised here if its wrong
        await spec_tel_obj.set_lamp(CHANGED_LAMP_BOOL)
        socket_obj.send.assert_called_once_with(LAMP_SET.encode())


@pytest.mark.asyncio
async def test_set_lamp():
    """
    Test full set_lamp() call
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        await spec_tel_obj.set_lamp(CHANGED_LAMP_BOOL)
        assert dummy_spec_obj.lamp == CHANGED_LAMP_INT


@pytest.mark.asyncio
async def test_set_lamp_bad_response(loguru_caplog):
    """
    Test recieving an unexpected response from set_lamp()
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        dummy_spec_obj.handle_set_lamp_request = lambda request: ""
        await spec_tel_obj.set_lamp(CHANGED_LAMP_BOOL)
        assert "Negative acknowledgement in response" in loguru_caplog.text
