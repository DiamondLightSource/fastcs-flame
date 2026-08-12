import asyncio
import multiprocessing as mp
from contextlib import asynccontextmanager
from socket import socket

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


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
        await close_non_blocking_socket(dummy_spectrometer_object.server_socket)
        await close_non_blocking_socket(dummy_spectrometer_object.connection)


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
        yield dummy_spec_obj, spec_tel_obj, read_pipe_end
