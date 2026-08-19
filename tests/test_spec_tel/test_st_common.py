import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 7023


async def run_dummy_spectrometer(dummy_spec_obj: DummySpectrometer):
    """
    Calls run on a passed in dummy spectrometer

    Waits for the tasks to finnish
    This wont happen unless the disconnect() method is called on the object
    For this reason this function is usually run as a new task
    Guarantees disconnect will be called if an error is raised by run()
    """
    try:
        await dummy_spec_obj.start()
        if dummy_spec_obj.listen_task is not None:
            await asyncio.gather(dummy_spec_obj.listen_task)
    finally:
        await dummy_spec_obj.disconnect()


@asynccontextmanager
async def start_spec_tel_object(spec_tel_obj: SpecTel):
    """
    Context manager for a given spectrometer telecommunicator

    Just calls connect and ensures disconnection
    """
    try:
        await spec_tel_obj.connect()
        yield spec_tel_obj
    finally:
        await spec_tel_obj.disconnect()


@asynccontextmanager
async def start_connection(
    dummy_spec_obj: DummySpectrometer | None = None,
    spec_tel_obj: SpecTel | None = None,
    ip=DEFAULT_IP,
    port=DEFAULT_PORT,
):
    """
    Connects a spectrometer telecommunicator to a dummy spectrometer

    dummy_spec_obj: Dummy spectrometer to be connected to
        Can pass in an existing object to allow modifying attribtues / methods
        If None is passed in (default) a dummy spectrometer will be created
    spec_tel_obj: Spectrometer telecommunicator to connect to the dummy object
        Can pass in an existing object to allow modifying attribtues / methods
        If None is passed in (default) a spectrometer telecommunicator will be created
    ip: IP to use for the connection
    port: Port to use for the connection
    Return: dummy_spectrometer and spectrometer telecommunicator
        that were passed in or created

    Context manager to ensure both objects are closed correctly
    Spec tel object should not be connected before passing in
    Objects will be disconnected at the end of the context manager
    but it shouldnt matter if they are disconnected earlier
    """

    if dummy_spec_obj is None:
        dummy_spec_obj = DummySpectrometer(port)
    if spec_tel_obj is None:
        spec_tel_obj = SpecTel(ip, port)

    asyncio.create_task(run_dummy_spectrometer(dummy_spec_obj))

    await dummy_spec_obj.waiting_for_connection.wait()

    async with start_spec_tel_object(spec_tel_obj=spec_tel_obj):
        yield (dummy_spec_obj, spec_tel_obj)


@asynccontextmanager
async def start_mock_socket(
    spec_tel_obj: SpecTel | None = None,
):
    """
    Creates a mock object that takes the place of the spec_tel socket object
    spec_tel_obj: Spectrometer telecommunicator to replace the socket of
        Can pass in an existing object to allow modifying attribtues / methods
        If None is passed in (default) a spectrometer telecommunicator will be created
    Return: spectrometer telecommunicator (passed in or created),
        the mock object that replaced the socket
        and the mock object that replaces the fetched event loop

    This method also patches the result of the asyncio.get_event_loop method
    with an AsyncMock object
    When using non-blocking sockets calls to connect and recieve data are actually
    made to the event loop with the socket as a parameter
    Mocking the event loop and returning it allows inspecting these calls
    """
    if spec_tel_obj is None:
        spec_tel_obj = SpecTel("", 0)

    spec_tel_obj.connected = True
    socket_obj = Mock()
    spec_tel_obj.socket_obj = socket_obj
    event_loop = AsyncMock()
    with patch(
        "fastcsflame.spectrometer_telecommunicator.asyncio.get_event_loop",
        return_value=event_loop,
    ):
        yield spec_tel_obj, socket_obj, event_loop


@pytest.mark.asyncio
async def test_start_connection():
    """
    Make sure start_connection() method doesnt throw errors
    and dummy spectrometer ends connected
    """

    async with start_connection() as (dummy_spec_obj, _):
        assert dummy_spec_obj.connection is not None
