import math
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from test_st_common import start_connection, start_mock_socket

from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator,
    UnexpectedResponseError,
)

# NOTE:
# The indexing of WCCs may look quite inconsistent
# However, there is a pattern
# order: The index the coefficients variable is raised to
#   e.g. a x^3, a has an order of 3 here
#   Constants' orders are 0
# index: The index in memory that a coefficient is stored at
# for equation a x^3 + b x^2 + c x + d
# coefficient : index
# a             4
# b             3
# c             2
# d             1
# Conversion is simplified so that order = index -1
# SPecTel deals in orders as they are more intuitive
# but it must send the spectrometer index's


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


@pytest.fixture(
    params=[
        0.00,
        1.00,
        0.00000001,
        10000000.0,
        5.0,
        5.5,
        5.555555555555,
        9.0,
        9.9,
        9.999999999999,
        1.111111111111,
        0.000000000001,
        100000000000.0,
        -1.00,
        -0.00000001,
        -10000000.0,
        -5.0,
        -5.5,
        -5.555555555555,
        -9.0,
        -9.9,
        -9.999999999999,
        -1.111111111111,
        -0.000000000001,
        -100000000000.0,
    ]
)
def sample_float(request):
    return request.param


@pytest.mark.asyncio
async def test_float_to_str14(sample_float):
    str_float = SpectrometerTelecommunicator._float_to_str14(sample_float)

    rounded_sample_float = float(f"{Decimal(sample_float):.7e}")
    assert math.isclose(rounded_sample_float, float(str_float))

    # Format should be:
    # (-)X.XXXXXXXe(-)XX

    # Should have no positive signs
    assert str_float.find("+") == -1

    if sample_float < 0:
        assert str_float[0] == "-"
        # Taking off the - at the start makes the rest of testing easier
        str_float = str_float[1:]
    if abs(sample_float) < 1.0 and sample_float != 0:
        assert str_float[10] == "-"
        str_float = str_float[:10] + str_float[11:]

    # Should be no negative signs left
    assert str_float.find("-") == -1

    assert len(str_float) == 12
    # Check decimal point position
    assert str_float[1] == "."
    # Check exponent sign position
    assert str_float[9] == "e"
