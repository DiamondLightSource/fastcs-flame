import asyncio
from unittest.mock import patch

import pytest
from test_common import (
    DEFAULT_IP,
    DEFAULT_PORT,
    run_dummy_spectrometer,
    start_connection,
    start_spec_tel_object,
)

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)

DEFAULT_SLEEP_TIME = 2


@pytest.mark.asyncio
async def test_connection():
    dummy_spec_obj = DummySpectrometer(DEFAULT_PORT)
    asyncio.create_task(run_dummy_spectrometer(dummy_spec_obj))

    await dummy_spec_obj.waiting_for_connection.wait()

    spec_tel_obj = SpecTel(DEFAULT_IP, DEFAULT_PORT)

    async with start_spec_tel_object(spec_tel_obj=spec_tel_obj):
        assert spec_tel_obj.connected


@pytest.mark.asyncio
async def test_bad_socket():
    spec_tel_obj = SpecTel(DEFAULT_IP, DEFAULT_PORT)
    with pytest.raises((ConnectionRefusedError, ConnectionResetError)):
        async with start_spec_tel_object(spec_tel_obj=spec_tel_obj):
            pass


@pytest.mark.asyncio
async def test_bad_initial_connection_message(loguru_caplog):

    with patch("dummy_spectrometer.TELNET_STARTUP_MESSAGE", b"\x15"):
        async with start_connection() as (_, _):
            assert "Unexpected connection message recieved: " in loguru_caplog.text


@pytest.mark.asyncio
async def test_device_connection_lost():
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        await asyncio.sleep(DEFAULT_SLEEP_TIME)
        await dummy_spec_obj.disconnect()
        assert not spec_tel_obj.connected


@pytest.mark.asyncio
async def test_reconnection():
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        await asyncio.sleep(DEFAULT_SLEEP_TIME)
        await dummy_spec_obj.disconnect()
        await asyncio.sleep(1.0)
        assert not spec_tel_obj.connected

        await asyncio.sleep(DEFAULT_SLEEP_TIME)
        asyncio.create_task(run_dummy_spectrometer(dummy_spec_obj))
        await dummy_spec_obj.waiting_for_connection.wait()
        await spec_tel_obj.restart_connection()
        assert spec_tel_obj.connected

        await asyncio.sleep(DEFAULT_SLEEP_TIME)


@pytest.mark.asyncio
async def test_device_already_connected():
    async with start_connection() as (_, _):
        spec_tel_obj_2 = SpecTel(DEFAULT_IP, DEFAULT_PORT)

        with pytest.raises(TimeoutError):
            async with start_spec_tel_object(spec_tel_obj=spec_tel_obj_2):
                pass
