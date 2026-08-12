import asyncio
from contextlib import asynccontextmanager

import pytest

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 7023


async def start_dummy_spectrometer(dummy_spec_obj: DummySpectrometer):
    try:
        await dummy_spec_obj.run()
    finally:
        await dummy_spec_obj.disconnect()


@asynccontextmanager
async def start_spec_tel_object(
    spec_tel_obj: SpecTel | None = None, ip=DEFAULT_IP, port=DEFAULT_PORT
):
    if spec_tel_obj is None:
        spec_tel_obj = SpecTel(ip, port)
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

    if dummy_spec_obj is None:
        dummy_spec_obj = DummySpectrometer(port)

    asyncio.create_task(start_dummy_spectrometer(dummy_spec_obj))

    await dummy_spec_obj.waiting_for_connection.wait()

    async with start_spec_tel_object(
        spec_tel_obj=spec_tel_obj, ip=ip, port=port
    ) as spec_tel_obj:
        yield (dummy_spec_obj, spec_tel_obj)


@pytest.mark.asyncio
async def test_start_connection():

    async with start_connection() as (_, spec_tel_obj):
        assert spec_tel_obj.connected
