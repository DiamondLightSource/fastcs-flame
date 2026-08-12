import asyncio
import multiprocessing as mp
from contextlib import asynccontextmanager

import pytest

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


def start_dummy_spectrometer(
    port: int, dummy_spec_obj: DummySpectrometer | None = None, write_pipe=None
):
    if dummy_spec_obj is None:
        dummy_spec_obj = DummySpectrometer(port, pipe=write_pipe)
    asyncio.run(run_dummy_spectrometer(dummy_spec_obj))


async def run_dummy_spectrometer(dummy_spectrometer_object: DummySpectrometer):
    try:
        await dummy_spectrometer_object.run()
    finally:
        await dummy_spectrometer_object.disconnect()


@asynccontextmanager
async def start_spec_tel_object(
    spec_tel_obj: SpecTel | None = None, ip="127.0.0.1", port=7016
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
    ip="127.0.0.1",
    port=7016,
):
    read_pipe_end, write_pipe_end = mp.Pipe(False)

    context = mp.get_context()
    process = context.Process(
        target=start_dummy_spectrometer,
        args=[port, dummy_spec_obj],
        kwargs={"write_pipe": write_pipe_end},
    )
    process.start()

    recieved_message = read_pipe_end.recv()
    assert recieved_message == "accepting"

    async with start_spec_tel_object(
        spec_tel_obj=spec_tel_obj, ip=ip, port=port
    ) as spec_tel_obj:
        yield (dummy_spec_obj, spec_tel_obj, read_pipe_end)


@pytest.mark.asyncio
async def test_start_connection():

    async with start_connection() as (_, spec_tel_obj, _):
        assert spec_tel_obj.connected
