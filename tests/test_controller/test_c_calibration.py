import asyncio
from unittest.mock import AsyncMock

import pytest
from fastcs.attributes import AttrRW
from test_c_common import controller_and_mock_objects

from fastcsflame.calibration_subcontroller import CalibrationSubcontroller
from fastcsflame.flame_controller import FlameController
from fastcsflame.flame_controller_attributes import SpectrommeterWCCIORef
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError

wcc_order_mapping: dict[int, str] = {
    0: "zero_order_wcc",
    1: "first_order_wcc",
    2: "second_order_wcc",
    3: "third_order_wcc",
}


def get_order_attribute(
    controller: FlameController, order: int
) -> AttrRW[float, SpectrommeterWCCIORef]:

    calibration_subcontroller = controller.sub_controllers["Calibration"]
    assert isinstance(calibration_subcontroller, CalibrationSubcontroller)

    match order:
        case 0:
            return calibration_subcontroller.zero_order_wcc
        case 1:
            return calibration_subcontroller.first_order_wcc
        case 2:
            return calibration_subcontroller.second_order_wcc
        case 3:
            return calibration_subcontroller.third_order_wcc
    raise ValueError


@pytest.mark.asyncio
async def test_initialisation(wcc_details, loguru_caplog):
    """
    Test wcc PVs are initialised correctly
    """
    order, default_value, _ = wcc_details
    spec_tel_mock = AsyncMock()

    spec_tel_mock.get_wcc = AsyncMock(return_value=default_value)

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    assert get_order_attribute(flame_controller, order).get() == round(default_value, 2)


@pytest.mark.asyncio
async def test_set_wcc(wcc_details, loguru_caplog):
    """
    Test setting the wcc PVs
    """
    order, _, change_value = wcc_details

    spec_tel_mock = AsyncMock()

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await get_order_attribute(flame_controller, order).put(change_value)
    spec_tel_mock.set_wcc.assert_awaited_once_with(order, round(change_value, 2))


# Test hidden for now
# Wont work until FastCS created coroutines can be closed manually
# or are closed on connect exceptions
@pytest.mark.asyncio
async def _test_bad_wcc_get(loguru_caplog):
    spec_tel_mock = AsyncMock()

    spec_tel_mock.get_wcc = AsyncMock(side_effect=UnexpectedResponseError)

    (
        task_pointer,
        _,
        spec_tel_mock,
        _,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await asyncio.gather(task_pointer)

    assert isinstance(error_queue.pop(), UnexpectedResponseError)


@pytest.mark.asyncio
async def test_bad_wcc_set(loguru_caplog):
    """
    Test raising an error from the set wcc method
    """
    spec_tel_mock = AsyncMock()
    spec_tel_mock.set_wcc = AsyncMock(side_effect=UnexpectedResponseError)

    (
        _,
        flame_controller,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await get_order_attribute(flame_controller, 0).put(0.000)

    assert "Recieved unexpected response from wcc set request" in loguru_caplog.text
