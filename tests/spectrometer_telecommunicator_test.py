import asyncio
import multiprocessing

import pytest

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


def setup_dummy_spectrometer(port: int):
    dummy_spectrometer = DummySpectrometer(port)
    asyncio.run(dummy_spectrometer.start())
    print("closing")


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
    spec_tel_object.connect()

    # Might not be necessary??
    if SpecTel.socket_obj is not None:
        SpecTel.socket_obj.send(b"")

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_get_version():
    spec_tel_object = await spec_tel_coroutine()
    spec_tel_object.connect()

    spec_tel_object.get_version()

    if SpecTel.socket_obj is not None:
        SpecTel.socket_obj.send(b"")

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_get_integration_time():
    spec_tel_object = await spec_tel_coroutine()
    spec_tel_object.connect()

    spec_tel_object.get_integration_time()

    if SpecTel.socket_obj is not None:
        SpecTel.socket_obj.send(b"")

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_set_integration_time():
    spec_tel_object = await spec_tel_coroutine()
    spec_tel_object.connect()

    old_integration_time = spec_tel_object.get_integration_time()
    new_integration_time = old_integration_time + 1
    spec_tel_object.set_integration_time(new_integration_time)

    assert new_integration_time == spec_tel_object.get_integration_time()

    if SpecTel.socket_obj is not None:
        SpecTel.socket_obj.send(b"")

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_get_last_scan():
    spec_tel_object = await spec_tel_coroutine()
    spec_tel_object.connect()

    spec_tel_object.get_last_scan()

    if SpecTel.socket_obj is not None:
        SpecTel.socket_obj.send(b"")

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()


@pytest.mark.asyncio
async def test_scan():
    spec_tel_object = await spec_tel_coroutine()
    spec_tel_object.connect()

    last_last_value = spec_tel_object.get_last_scan()[-1]

    new_last_value = spec_tel_object.scan()[-1]

    assert last_last_value != new_last_value

    if SpecTel.socket_obj is not None:
        SpecTel.socket_obj.send(b"")

    if spec_tel_object.socket_obj is not None:
        spec_tel_object.socket_obj.close()
