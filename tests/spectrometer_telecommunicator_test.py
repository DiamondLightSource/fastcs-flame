import asyncio
import multiprocessing

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


def setup_dummy_spectrometer(port: int):
    dummy_spectrometer = DummySpectrometer(port)
    asyncio.run(dummy_spectrometer.start())


async def test_test():

    mp_context = multiprocessing.get_context()

    server_process = mp_context.Process(target=setup_dummy_spectrometer, args=[7016])
    server_process.start()

    await asyncio.sleep(2)

    spec_tel_obj = SpecTel("127.0.0.1", 7016)
    spec_tel_obj.connect()

    print("testing!!")
    assert True
    if SpecTel.socket_obj is not None:
        SpecTel.socket_obj.send(b"")


if __name__ == "__main__":
    asyncio.run(test_test())
