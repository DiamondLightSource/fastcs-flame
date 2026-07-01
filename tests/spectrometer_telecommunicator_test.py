import asyncio
import multiprocessing
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

        def new_get_version() -> bytes:
            return dummy_spectrometer.wrap_response("v", "", delimeter=b"\x15")

        dummy_spectrometer.get_version = new_get_version
    asyncio.run(dummy_spectrometer.start(startup_message=startup_message))


# TODO: Turn this into some sort of fixture
# Does this work for async functions??
async def spec_tel_coroutine():
    """
    Function that returns an unconnected spectrometer telecommunicator object
    Pointing to a dummy spectrometer running on another process
    """

    mp_context = multiprocessing.get_context()

    server_process = mp_context.Process(target=setup_dummy_spectrometer, args=[7016])
    server_process.start()

    await asyncio.sleep(1)

    return SpecTel("127.0.0.1", 7016)


@pytest.mark.asyncio
async def test_connection():
    spec_tel_object = await spec_tel_coroutine()
    await spec_tel_object.connect()

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_bad_socket():

    spec_tel_object = SpecTel("127.0.0.1", 7016)

    with pytest.raises(ConnectionRefusedError):
        await spec_tel_object.connect()

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


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
    with pytest.raises(UnexpectedResponseError):
        await spec_tel_object.connect()
    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_device_already_connected():
    spec_tel_object = await spec_tel_coroutine()

    socket_obj = socket()
    socket_obj.connect(("127.0.0.1", 7016))
    socket_obj.setblocking(False)

    loop = asyncio.get_event_loop()
    await loop.sock_recv(socket_obj, 1024)

    with pytest.raises(TimeoutError):
        await spec_tel_object.connect()
    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()
    socket_obj.close()


@pytest.mark.asyncio
async def test_get_version():
    spec_tel_object = await spec_tel_coroutine()
    await spec_tel_object.connect()

    await spec_tel_object.get_version()

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


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
    await spec_tel_object.connect()

    with pytest.raises(UnexpectedResponseError):
        await spec_tel_object.get_version()

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_get_integration_time():
    spec_tel_object = await spec_tel_coroutine()
    await spec_tel_object.connect()

    await spec_tel_object.get_integration_time()

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_set_integration_time():
    spec_tel_object = await spec_tel_coroutine()
    await spec_tel_object.connect()

    old_integration_time = await spec_tel_object.get_integration_time()
    new_integration_time = old_integration_time + 1
    await spec_tel_object.set_integration_time(new_integration_time)

    assert new_integration_time == spec_tel_object.get_integration_time()

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_get_last_scan():
    spec_tel_object = await spec_tel_coroutine()
    await spec_tel_object.connect()

    await spec_tel_object.get_last_scan()

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_scan():
    spec_tel_object = await spec_tel_coroutine()
    await spec_tel_object.connect()

    last_last_value = (await spec_tel_object.get_last_scan())[-1]

    new_last_value = (await spec_tel_object.scan())[-1]

    assert last_last_value != new_last_value

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()
