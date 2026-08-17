from unittest.mock import AsyncMock

import pytest
from test_common import start_connection, start_mock_socket

from common import lists_equal
from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError

LAST_SCAN_DATA = list(range(100))
CHANGED_SCAN_DATA = list(range(1, 101))

GET_LAST_SCAN_DATA = "Z"
SCAN = "S"

GET_LAST_SCAN_RESPONSE = DummySpectrometer.wrap_response(
    GET_LAST_SCAN_DATA,
    "65535 0 1 8 0 0 0 " + " ".join([str(x) for x in LAST_SCAN_DATA]) + " 65533 ",
)
SCAN_RESPONSE = DummySpectrometer.wrap_response(
    SCAN,
    "65535 0 1 8 0 0 0 " + " ".join([str(x) for x in CHANGED_SCAN_DATA]) + " 65533 ",
    delimeter=b"\x02",
)


@pytest.mark.asyncio
async def test_get_last_scan_data_message():
    """
    Test the message sent when get_last_scan() is called
    """
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        event_loop.sock_recv = AsyncMock(return_value=GET_LAST_SCAN_RESPONSE)
        await spec_tel_obj.get_last_scan()
        socket_obj.send.assert_called_once_with(GET_LAST_SCAN_DATA.encode())


@pytest.mark.asyncio
async def test_get_last_scan_data_decoding():
    """
    Test the decoding of the get_last_scan() recieved data message
    """
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        event_loop.sock_recv = AsyncMock(return_value=GET_LAST_SCAN_RESPONSE)
        get_last_scan_response = await spec_tel_obj.get_last_scan()
        assert lists_equal(get_last_scan_response, LAST_SCAN_DATA)


@pytest.mark.asyncio
async def test_get_last_scan_data():
    """
    Test full get_last_scan() call
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        recieved_last_scan = await spec_tel_obj.get_last_scan()
        assert lists_equal(dummy_spec_obj.last_scan_data, recieved_last_scan)


@pytest.mark.asyncio
async def test_get_last_scan_data_short_response():
    """
    Test get_last_scan() when the recieved message is shorter than expected
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):

        async def empty_return_awaitable():
            return "one thousand"

        dummy_spec_obj.handle_get_last_scan_request = empty_return_awaitable
        with pytest.raises(UnexpectedResponseError):
            await spec_tel_obj.get_last_scan()


@pytest.mark.asyncio
async def test_get_last_scan_data_bad_response():
    """
    Test get_last_scan() when the recieved message is unexpected
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):

        async def empty_return_awaitable():
            return "one hundred and twenty two thousand two hundred and thirty three"

        dummy_spec_obj.handle_get_last_scan_request = empty_return_awaitable
        with pytest.raises(UnexpectedResponseError):
            await spec_tel_obj.get_last_scan()


@pytest.mark.asyncio
async def test_scan_message():
    """
    Test the message sent when scan() is called
    """
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        event_loop.sock_recv = AsyncMock(return_value=SCAN_RESPONSE)
        await spec_tel_obj.scan()
        socket_obj.send.assert_called_once_with(SCAN.encode())


@pytest.mark.asyncio
async def test_scan_decoding():
    """
    Test the decoding of the response to a scan() call
    """
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        event_loop.sock_recv = AsyncMock(return_value=SCAN_RESPONSE)
        scan_data_recieved = await spec_tel_obj.scan()
        assert lists_equal(scan_data_recieved, CHANGED_SCAN_DATA)


@pytest.mark.asyncio
async def test_scan():
    """
    Test full scan() call
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        recieved_last_scan = await spec_tel_obj.scan()
        assert lists_equal(dummy_spec_obj.last_scan_data, recieved_last_scan)


@pytest.mark.asyncio
async def test_scan_data_short_response():
    """
    Test recieving a shorter than expect message from scan()
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):

        async def empty_return_awaitable():
            return "one thousand"

        dummy_spec_obj.handle_scan_request = empty_return_awaitable
        with pytest.raises(UnexpectedResponseError):
            await spec_tel_obj.scan()


@pytest.mark.asyncio
async def test_scan_data_bad_response():
    """
    Test recieving a bad response from scan()
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):

        async def empty_return_awaitable():
            return "one hundred and twenty two thousand two hundred and thirty three"

        dummy_spec_obj.handle_scan_request = empty_return_awaitable
        with pytest.raises(UnexpectedResponseError):
            await spec_tel_obj.scan()
