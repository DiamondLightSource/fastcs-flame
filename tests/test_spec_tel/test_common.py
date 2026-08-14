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
    try:
        await dummy_spec_obj.run()
    finally:
        await dummy_spec_obj.disconnect()


@asynccontextmanager
async def start_spec_tel_object(spec_tel_obj: SpecTel):
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

    async with start_connection() as (dummy_spec_obj, _):
        assert dummy_spec_obj.connected
