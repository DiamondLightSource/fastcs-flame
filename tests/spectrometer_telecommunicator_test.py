import asyncio
import multiprocessing
from contextlib import asynccontextmanager
from socket import socket

import pytest

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError


def setup_dummy_spectrometer(port: int):
    dummy_spectrometer = DummySpectrometer(port)
    asyncio.run(dummy_spectrometer.start())
    print("closing")


def custom_setup_dummy_spectrometer(
    port: int,
    startup_message: bytes = b"\xff\xfa,k\x0f\xff\xf0",
    bad_version_response=False,
):
    dummy_spectrometer = DummySpectrometer(port)
    if bad_version_response:

        def new_get_version() -> str:
            return ""

        dummy_spectrometer.handle_get_version_request = new_get_version
    asyncio.run(dummy_spectrometer.start(startup_message=startup_message))


def ephemeral_dummy_spectrometer(
    port: int, disconnect_after_time: float, reconnect_after_time: float | None = None
):
    dummy_spectrometer = DummySpectrometer(port)

    async def run_with_disconnect():

        async def close_socket():
            await asyncio.sleep(disconnect_after_time)
            dummy_spectrometer.connection.close()
            if reconnect_after_time is not None:
                await asyncio.sleep(reconnect_after_time)
                dummy_spectrometer.server_socket = socket()
                dummy_spectrometer.server_socket.bind(("", port))
                await dummy_spectrometer.start()

        task = asyncio.create_task(close_socket())

        await dummy_spectrometer.start()
        task.cancel()

    try:
        asyncio.run(run_with_disconnect())
    finally:
        dummy_spectrometer.server_socket.close()
        dummy_spectrometer.connection.close()


@asynccontextmanager
async def spec_tel_coroutine():
    """
    Function that returns an unconnected spectrometer telecommunicator object
    Pointing to a dummy spectrometer running on another process
    """

    mp_context = multiprocessing.get_context()

    server_process = mp_context.Process(target=setup_dummy_spectrometer, args=[7016])
    server_process.start()

    await asyncio.sleep(1)

    spec_tel_object = SpecTel("127.0.0.1", 7016)
    try:
        yield spec_tel_object
    finally:
        await spec_tel_object.disconnect()


async def close_non_blocking_socket(socket_obj: socket | None):
    """
    Makes sure non blocking sockets close properly

    Improperly closed sockets can lead to future tests failing as the port they tried
    to bind to is already in use (by the previous, finished test)
    """
    if socket_obj is None:
        return
    socket_obj.close()
    # This method is quite crude but it seems to have a high success rate
    # Ideally you would run recv from the socket until a b'' is recieved
    # This would also require a timeout incase nothing is ever recieved
    # And im not sure what you would even do in this case when you already
    # tried to close it??
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_connection():
    async with spec_tel_coroutine() as spec_tel_object:
        await spec_tel_object.connect()


@pytest.mark.asyncio
async def test_bad_socket():

    spec_tel_object = SpecTel("127.0.0.1", 7016)

    try:
        # Can raise either of these exceptions??
        # Doesnt seem to act deterministically
        with pytest.raises((ConnectionRefusedError, ConnectionResetError)):
            await spec_tel_object.connect()
    finally:
        await spec_tel_object.disconnect()


@pytest.mark.asyncio
async def test_bad_initial_connection_message():

    mp_context = multiprocessing.get_context()

    server_process = mp_context.Process(
        target=custom_setup_dummy_spectrometer,
        args=[7016],
        kwargs={"startup_message": b"\xf0\xfa,k\x0f\xff\xff"},
    )
    server_process.start()

    await asyncio.sleep(1)

    spec_tel_object = SpecTel("127.0.0.1", 7016)
    try:
        with pytest.raises(UnexpectedResponseError):
            await spec_tel_object.connect()
    finally:
        await spec_tel_object.disconnect()


@pytest.mark.asyncio
async def test_device_connection_lost():
    mp_context = multiprocessing.get_context()
    server_process = mp_context.Process(
        target=ephemeral_dummy_spectrometer,
        args=[7016, 8.0],
    )
    server_process.start()

    await asyncio.sleep(1)

    spec_tel_object = SpecTel("127.0.0.1", 7016)
    try:
        with pytest.raises(TimeoutError):
            await spec_tel_object.connect()
            await asyncio.sleep(15)
            await spec_tel_object.get_version()
    finally:
        await spec_tel_object.disconnect()


@pytest.mark.asyncio
async def test_device_already_connected():
    async with spec_tel_coroutine() as spec_tel_object:
        socket_obj = socket()
        try:
            socket_obj.connect(("127.0.0.1", 7016))
            socket_obj.setblocking(False)

            loop = asyncio.get_event_loop()
            await loop.sock_recv(socket_obj, 1024)

            with pytest.raises(TimeoutError):
                await spec_tel_object.connect()
        finally:
            await close_non_blocking_socket(socket_obj)


@pytest.mark.asyncio
async def test_get_version():
    async with spec_tel_coroutine() as spec_tel_object:
        await spec_tel_object.connect()

        await spec_tel_object.get_version()


@pytest.mark.asyncio
async def test_invalid_response():
    mp_context = multiprocessing.get_context()

    server_process = mp_context.Process(
        target=custom_setup_dummy_spectrometer,
        args=[7016],
        kwargs={"bad_version_response": True},
    )
    server_process.start()

    await asyncio.sleep(1)

    spec_tel_object = SpecTel("127.0.0.1", 7016)
    try:
        await spec_tel_object.connect()

        with pytest.raises(UnexpectedResponseError):
            await spec_tel_object.get_version()
    finally:
        await spec_tel_object.disconnect()


@pytest.mark.asyncio
async def test_get_integration_time():
    async with spec_tel_coroutine() as spec_tel_object:
        await spec_tel_object.connect()

        await spec_tel_object.get_integration_time()


@pytest.mark.asyncio
async def test_set_integration_time():
    async with spec_tel_coroutine() as spec_tel_object:
        await spec_tel_object.connect()

        old_integration_time = await spec_tel_object.get_integration_time()
        new_integration_time = old_integration_time + 1
        await spec_tel_object.set_integration_time(new_integration_time)

        assert new_integration_time == await spec_tel_object.get_integration_time()


@pytest.mark.asyncio
async def test_get_last_scan():
    async with spec_tel_coroutine() as spec_tel_object:
        await spec_tel_object.connect()

        await spec_tel_object.get_last_scan()


@pytest.mark.asyncio
async def test_scan():
    async with spec_tel_coroutine() as spec_tel_object:
        await spec_tel_object.connect()

        last_last_value = (await spec_tel_object.get_last_scan())[-1]

        new_last_value = (await spec_tel_object.scan())[-1]

        assert last_last_value != new_last_value
