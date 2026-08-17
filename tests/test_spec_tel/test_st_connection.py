import asyncio
from unittest.mock import patch

import pytest
from test_st_common import (
    DEFAULT_IP,
    DEFAULT_PORT,
    run_dummy_spectrometer,
    start_connection,
    start_spec_tel_object,
)
from test_st_integration_time import CHANGED_INTEGRATION_TIME

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import NotConnectedError
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)

DEFAULT_SLEEP_TIME = 2
SCAN_TIME = 11


@pytest.mark.asyncio
async def test_connection():
    """
    Tests connect method
    """
    dummy_spec_obj = DummySpectrometer(DEFAULT_PORT)
    asyncio.create_task(run_dummy_spectrometer(dummy_spec_obj))

    await dummy_spec_obj.waiting_for_connection.wait()

    spec_tel_obj = SpecTel(DEFAULT_IP, DEFAULT_PORT)

    async with start_spec_tel_object(spec_tel_obj=spec_tel_obj):
        assert spec_tel_obj.connected


@pytest.mark.asyncio
async def test_bad_socket():
    """
    Test running connect() on a blocked port
    """
    # Create spectrometer telecommincator without a dummy spectrometer
    # to connect to
    spec_tel_obj = SpecTel(DEFAULT_IP, DEFAULT_PORT)
    # Can raise either error
    with pytest.raises((ConnectionRefusedError, ConnectionResetError)):
        async with start_spec_tel_object(spec_tel_obj=spec_tel_obj):
            pass


@pytest.mark.asyncio
async def test_bad_initial_connection_message(loguru_caplog):
    """
    Test connecting to a spectrometer that doesnt reply with the default
    telnet connection message
    """
    with patch("dummy_spectrometer.TELNET_STARTUP_MESSAGE", b"\x15"):
        async with start_connection() as (_, _):
            assert "Unexpected connection message recieved: " in loguru_caplog.text


@pytest.mark.asyncio
async def test_device_connection_lost():
    """
    Test the disconnection listener
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        await asyncio.sleep(DEFAULT_SLEEP_TIME)
        await dummy_spec_obj.disconnect()
        assert not spec_tel_obj.connected


@pytest.mark.asyncio
async def test_reconnection():
    """
    Test the restart_connection() method
    """
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

        # Sleep here because shutting down sockets
        # immediately after connecting can cause issues
        await asyncio.sleep(DEFAULT_SLEEP_TIME)


@pytest.mark.asyncio
async def test_device_already_connected():
    """
    Tests running connect() on a port that has already been connected to
    """
    async with start_connection() as (_, _):
        spec_tel_obj_2 = SpecTel(DEFAULT_IP, DEFAULT_PORT)

        with pytest.raises(TimeoutError):
            # Tries connecting the second telecommunicator to the dummy object
            # that the first is already connected to
            async with start_spec_tel_object(spec_tel_obj=spec_tel_obj_2):
                pass


@pytest.mark.asyncio
async def test_disconnect_during_scan():
    """
    Test loosing spectrometer connection whilst waiting for a response
    from a scan request
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):

        async def disconnect_dummy_after_time():
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            await dummy_spec_obj.disconnect()

        asyncio.create_task(disconnect_dummy_after_time())

        # In the programs current state theres actually quite a lot that happens here
        # Disconnect listener is paused because were expecting a response
        # Response should be b"" as the socket is closed
        # Upon recieving this, telecommunicator tries to restart connection
        # When connect() is run one of these errors is raised (like before)
        with pytest.raises((ConnectionRefusedError, ConnectionResetError)):
            await spec_tel_obj.scan()

        assert not spec_tel_obj.connected
        # This is the most check in the test
        # How it fails and disconnects is not too important
        # As long as the message_lock is not permanently locked
        assert not spec_tel_obj.message_lock.locked()


@pytest.mark.asyncio
async def test_disconnect_with_queue():
    """
    Test disconnecting spectrometer whilst there are pending messages in the queue
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        # Acquire the message lock so messages can be added to the queue
        # Without the executing immediately
        # This should NEVER be done in a practical situation
        await spec_tel_obj.message_lock.acquire()

        set_task = asyncio.create_task(
            spec_tel_obj.set_integration_time(CHANGED_INTEGRATION_TIME)
        )
        get_task = asyncio.create_task(spec_tel_obj.get_integration_time())

        await dummy_spec_obj.disconnect()
        # Release message lock so queued messages are sent
        spec_tel_obj.message_lock.release()

        with pytest.raises(NotConnectedError):
            set_task.result()

        with pytest.raises(NotConnectedError):
            get_task.result()

        assert not spec_tel_obj.connected
        assert not spec_tel_obj.message_lock.locked()
