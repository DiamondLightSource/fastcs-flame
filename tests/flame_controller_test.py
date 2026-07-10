import asyncio
import multiprocessing
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from fastcs.launch import FastCS
from fastcs.logging import configure_logging, logger
from pytest import LogCaptureFixture

from fastcsflame.flame_controller import FlameController
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError
from spectrometer_telecommunicator_test import setup_dummy_spectrometer


@pytest.fixture
def loguru_caplog(caplog) -> Generator[LogCaptureFixture]:
    configure_logging()
    handler_id = logger.add(caplog.handler, format="{message}", level="TRACE")
    yield caplog
    logger.remove(handler_id)


async def serve_fastcs(fastcs_instance: FastCS, error_queue: list[BaseException]):

    try:
        await fastcs_instance.serve(interactive=False)
    except BaseException as e:
        error_queue.append(e)
    finally:
        for controller in fastcs_instance._controllers:
            await controller.disconnect()


# cant be a fixture as it requires a running event loop
async def controller_and_mock_objects(
    loguru_caplog,
    spec_tel_mock: AsyncMock | None = None,
    file_builder_mock: AsyncMock | None = None,
):
    # configure_logging()
    logger.add(print)

    if spec_tel_mock is None:
        spec_tel_mock = AsyncMock()
    if file_builder_mock is None:
        file_builder_mock = AsyncMock()
    error_queue: list[BaseException] = []
    with patch(
        "fastcsflame.flame_controller.SpecTel",
        return_value=spec_tel_mock,
    ):
        with patch(
            "fastcsflame.flame_controller.FileBuilder",
            return_value=file_builder_mock,
        ):
            flame_controller = FlameController(
                "172.23.91.5",
                7016,
                default_file_path="",
                default_file_name="",
            )
            flame_controller.set_path(["FLAME"])
            fastcs = FastCS(flame_controller, [])

            task = asyncio.create_task(serve_fastcs(fastcs, error_queue))

            for _ in range(11):
                if "Starting FastCS" in loguru_caplog.text:
                    return (
                        task,
                        flame_controller,
                        spec_tel_mock,
                        file_builder_mock,
                        error_queue,
                    )
                await asyncio.sleep(1)
            raise TimeoutError


def lists_equal(list1, list2):
    if len(list1) != len(list2):
        return False
    return all(list1[i] == list2[i] for i in range(len(list1)))


@pytest.mark.asyncio
async def test_controller_and_mock_objects(loguru_caplog):

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog)

    assert True


@pytest.mark.asyncio
async def test_controller_initialisation(loguru_caplog):

    spec_tel_mock = AsyncMock()
    spec_tel_mock.integration_time = 10

    async def get_integration_time():
        return spec_tel_mock.integration_time

    spec_tel_mock.get_integration_time = get_integration_time
    spec_tel_mock.last_scan_data = np.array(range(10))

    async def get_last_scan():
        return spec_tel_mock.last_scan_data

    spec_tel_mock.get_last_scan = get_last_scan

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    spec_tel_mock.connect.assert_called()
    assert flame_controller.integration_time.get() == spec_tel_mock.integration_time
    assert lists_equal(flame_controller.scan_data.get(), spec_tel_mock.last_scan_data)


@pytest.mark.asyncio
async def test_set_integration_time(loguru_caplog):

    spec_tel_mock = AsyncMock()
    spec_tel_mock.integration_time = 10

    async def get_integration_time():
        return spec_tel_mock.integration_time

    def set_integration_time(integration_time: int):
        spec_tel_mock.integration_time = integration_time

    spec_tel_mock.get_integration_time = get_integration_time
    spec_tel_mock.set_integration_time = set_integration_time
    spec_tel_mock.last_scan_data = np.array(range(10))

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    new_integration_time = spec_tel_mock.integration_time + 1
    await flame_controller.integration_time.put(new_integration_time)
    assert spec_tel_mock.integration_time == new_integration_time


@pytest.mark.asyncio
async def test_scan_data_command(loguru_caplog):
    spec_tel_mock = AsyncMock()
    spec_tel_mock.last_scan_data = np.array(range(10))

    async def get_last_scan():
        return spec_tel_mock.last_scan_data

    async def scan():
        spec_tel_mock.last_scan_data = np.array(range(10)) + 10
        return spec_tel_mock.last_scan_data

    spec_tel_mock.get_last_scan = get_last_scan
    spec_tel_mock.scan = scan

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    old_scan_data = flame_controller.scan_data.get()
    await flame_controller.single_scan()
    new_scan_data = flame_controller.scan_data.get()

    assert not lists_equal(old_scan_data, new_scan_data)
    assert lists_equal(new_scan_data, spec_tel_mock.last_scan_data)


# Test hidden for now
# Wont work until FastCS created coroutines can be closed manually
# or are closed on connect exceptions
@pytest.mark.asyncio
async def _test_bad_connection(loguru_caplog):
    spec_tel_mock = AsyncMock()

    async def connect():
        raise UnexpectedResponseError

    spec_tel_mock.connect = connect

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    task_pointer.cancel()
    await asyncio.gather(task_pointer)

    assert isinstance(error_queue.pop(), UnexpectedResponseError)


# Similar for this test
@pytest.mark.asyncio
async def _test_bad_integration_time_get(loguru_caplog):
    spec_tel_mock = AsyncMock()

    async def get_integration_time():
        raise UnexpectedResponseError

    spec_tel_mock.get_integration_time = get_integration_time

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await asyncio.gather(task_pointer)

    assert isinstance(error_queue.pop(), UnexpectedResponseError)


# Similar for this test
@pytest.mark.asyncio
async def _test_bad_last_scan_data_get(loguru_caplog):
    spec_tel_mock = AsyncMock()

    async def get_last_scan():
        raise UnexpectedResponseError

    spec_tel_mock.get_integration_time = get_last_scan

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await asyncio.gather(task_pointer)

    assert isinstance(error_queue.pop(), UnexpectedResponseError)


@pytest.mark.asyncio
async def test_bad_integration_time_set(loguru_caplog):
    spec_tel_mock = AsyncMock()

    spec_tel_mock.integration_time = 10

    async def get_integration_time():
        return spec_tel_mock.integration_time

    def set_integration_time(integration_time: int):
        raise UnexpectedResponseError

    spec_tel_mock.get_integration_time = get_integration_time
    spec_tel_mock.set_integration_time = set_integration_time

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await flame_controller.integration_time.put(10)

    assert "UnexpectedResponseError" in loguru_caplog.text


@pytest.mark.asyncio
async def test_bad_scan_command(loguru_caplog):
    spec_tel_mock = AsyncMock()

    spec_tel_mock.last_scan_data = list(range(10))

    async def get_scan_data():
        return spec_tel_mock.last_scan_data

    def scan():
        raise UnexpectedResponseError

    spec_tel_mock.get_scan_data = get_scan_data
    spec_tel_mock.scan = scan

    (
        task_pointer,
        flame_controller,
        spec_tel_mock,
        file_builder_mock,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    await flame_controller.single_scan()

    assert (
        "Spectrometer gave unexpected response from scan trigger attempt: "
        in loguru_caplog.text
    )


@pytest.mark.asyncio
async def test_interrupt_scan(tmp_path):
    mp_context = multiprocessing.get_context()

    server_process = mp_context.Process(target=setup_dummy_spectrometer, args=[7016])
    server_process.start()

    await asyncio.sleep(1)

    flame_controller = FlameController(
        "127.0.0.1", 7016, default_file_path=tmp_path, default_file_name="data"
    )

    flame_controller.set_path(["FLAME"])
    fastcs = FastCS(flame_controller, [])

    asyncio.create_task(fastcs.serve(interactive=False))

    # TODO: Remove magic numbers
    await asyncio.sleep(3)

    asyncio.create_task(flame_controller.single_scan())

    await asyncio.sleep(1)

    await flame_controller.integration_time.put(8)

    await asyncio.sleep(11)

    assert flame_controller.integration_time.get() == 8

    if flame_controller.spec_tel_obj.socket_obj is not None:
        flame_controller.spec_tel_obj.socket_obj.close()
