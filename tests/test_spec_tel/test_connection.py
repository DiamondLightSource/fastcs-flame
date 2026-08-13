import asyncio

import pytest
from test_common import (
    DEFAULT_IP,
    DEFAULT_PORT,
    run_dummy_spectrometer,
    start_spec_tel_object,
)

from dummy_spectrometer import DummySpectrometer
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


@pytest.mark.asyncio
async def test_connection():
    dummy_spec_obj = DummySpectrometer(DEFAULT_PORT)
    asyncio.create_task(run_dummy_spectrometer(dummy_spec_obj))

    await dummy_spec_obj.waiting_for_connection.wait()

    spec_tel_obj = SpecTel(DEFAULT_IP, DEFAULT_PORT)

    async with start_spec_tel_object(spec_tel_obj=spec_tel_obj):
        assert spec_tel_obj.connected
