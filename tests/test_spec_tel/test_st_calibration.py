import math
from unittest.mock import AsyncMock

import pytest
from test_st_common import start_connection, start_mock_socket

from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator,
    UnexpectedResponseError,
)


@pytest.fixture(params=[0, 1, 2, 3])
def wcc_details(request):

    order = request.param
    default_values: dict[int, float] = {
        1: 178.89592,
        2: 0.38649029,
        3: -0.000018147914,
        4: -0.000000020812843,
    }
    change_values: dict[int, float] = {
        1: 178.89592,
        2: 0.38649029,
        3: -0.000018147914,
        4: -0.000000020812843,
    }

    return (order, default_values[order + 1], change_values[order + 1])


def get_request_message(order: int):
    return b"?x" + str(order + 1).encode("ascii") + b"\n"


def get_request_response(order: int, value: float):
    return (
        b"?x"
        + str(order + 1).encode("ascii")
        + b"\n\r\r\x06"
        + SpectrometerTelecommunicator._float_to_str14(value).encode("ascii")
        + b"\n\r\n\r> "
    )


def set_request_message(order: int, value: float):
    str14_no_underscore = SpectrometerTelecommunicator._float_to_str14(value)
    str14_with_underscore = str14_no_underscore[:1] + "_" + str14_no_underscore[1:]
    return (
        b"x"
        + str(order + 1).encode("ascii")
        + b"\r"
        + str14_with_underscore.encode("ascii")
        + b"\n"
    )


def set_request_response(order: int, value: float):
    return (
        b"x"
        + str(order + 1).encode("ascii")
        + b"\n\r\r"
        + SpectrometerTelecommunicator._float_to_str14(value).encode("ascii")
        + b"\n\r\n\r> "
    )


@pytest.mark.asyncio
async def test_get_wcc_message(wcc_details):
    """
    Test the message sent when get_wcc() is called
    """
    order, default_value, _ = wcc_details
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        # Simulate expected response so no errors are thrown
        # Easier than mocking all the various methods involved
        event_loop.sock_recv = AsyncMock(
            return_value=get_request_response(order, default_value)
        )
        await spec_tel_obj.get_wcc(order)
        socket_obj.send.assert_called_once_with(get_request_message(order))


@pytest.mark.asyncio
async def test_get_wcc_decoding(wcc_details):
    """
    Test the value returned when get_wcc() is called
    """
    order, default_value, _ = wcc_details
    async with start_mock_socket() as (spec_tel_obj, _, event_loop):
        event_loop.sock_recv = AsyncMock(
            return_value=get_request_response(order, default_value)
        )
        recieved_wcc = await spec_tel_obj.get_wcc(order)
        assert recieved_wcc == default_value


@pytest.mark.asyncio
async def test_get_wcc(wcc_details):
    """
    Test full integration time call
    """
    order, _, _ = wcc_details
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        recieved_wcc = await spec_tel_obj.get_wcc(order)
        assert math.isclose(recieved_wcc, float(dummy_spec_obj.wccs[order + 1]))


@pytest.mark.asyncio
async def test_get_wcc_bad_response():
    """
    Test recieving an unexpected response from get_wcc()
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        dummy_spec_obj.handle_get_wcc_request = lambda request: ""
        with pytest.raises(UnexpectedResponseError):
            await spec_tel_obj.get_wcc(1)


@pytest.mark.asyncio
async def test_set_wcc_message(wcc_details):
    order, _, change_value = wcc_details
    """
    Test the message sent when set_wcc() is called
    """
    async with start_mock_socket() as (spec_tel_obj, socket_obj, event_loop):
        event_loop.sock_recv = AsyncMock(
            return_value=set_request_response(order, change_value)
        )
        await spec_tel_obj.set_wcc(order, change_value)
        socket_obj.send.assert_called_once_with(
            set_request_message(order, change_value)
        )


@pytest.mark.asyncio
async def test_set_wcc(wcc_details):
    """
    Test fully set_wcc() call
    """
    order, _, change_value = wcc_details
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        await spec_tel_obj.set_wcc(order, change_value)
        assert math.isclose(float(dummy_spec_obj.wccs[order + 1]), change_value)


@pytest.mark.asyncio
async def test_set_wcc_bad_response(loguru_caplog):
    """
    Test recieving an unexpected response from set_wcc()
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        dummy_spec_obj.handle_set_wcc_request = lambda request: (0, "")
        with pytest.raises(UnexpectedResponseError):
            await spec_tel_obj.set_wcc(0, 1.0)
