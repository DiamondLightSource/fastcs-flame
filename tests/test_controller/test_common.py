import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastcs.launch import FastCS

from fastcsflame.flame_controller import FlameController
from fastcsflame.spectrometer_telecommunicator import UnexpectedResponseError


async def serve_fastcs(fastcs_instance: FastCS, error_queue: list[BaseException]):
    """
    Serves the given fastcs instance capturing the first error raised
    fastcs_instance: fastcs instance to run
    error_queue: Where to add the errors too
        More of a pointer really as only the first error raised is added
    """

    try:
        await fastcs_instance.serve(interactive=False)
    except BaseException as e:
        error_queue.append(e)
    finally:
        for controller in fastcs_instance._controllers:
            await controller.disconnect()


async def controller_and_mock_objects(
    loguru_caplog,
    spec_tel_mock: AsyncMock | None = None,
    file_builder_mock: Mock | None = None,
    timeout: int = 11,
    start_poll_period: int = 1,
) -> tuple[asyncio.Task, FlameController, AsyncMock, Mock, list[BaseException]]:
    """
    Creates a flame controller and starts FastCS with mock objects
    loguru_caplog: Log fixture from test
    spec_tel_mock: The object to replace the controllers spec_tel object with
        On None a blank mock object will be used
    file_builder_mock: The object to replace the controllers file_builder
        object with. On None a black mock object will be used
    timeout: Time to wait after attempting to start FastCS until raising
        a timeout exception (unless launch is successful)
    start_poll_period: The time between each poll to test if FastCS has started
    returns a tuple of:
        The task running the FastCS serve method
        The created controller object
        The spec_tel_mock object
        The file_builder mock object
        The queue of errors raised by FastCS
    Waits to return until it is confirmed FastCS has started
    Cant be a fixture as it requires a running event loop
    """

    if spec_tel_mock is None:
        spec_tel_mock = AsyncMock()
    if file_builder_mock is None:
        file_builder_mock = Mock()
    error_queue: list[BaseException] = []

    # Would be nice to do these context managers manually
    # Scopes could easily stack up with more objects
    with patch(
        "fastcsflame.flame_controller.SpecTel",
        return_value=spec_tel_mock,
    ):
        with patch(
            "fastcsflame.flame_controller.FileBuilder",
            return_value=file_builder_mock,
        ):
            flame_controller = FlameController(
                "",
                0,
                mount_path="",
                default_file_name="",
            )
            flame_controller.set_path(["FLAME"])
            fastcs = FastCS(flame_controller, [])

            task = asyncio.create_task(serve_fastcs(fastcs, error_queue))

            for _ in range(timeout):
                if "Starting FastCS" in loguru_caplog.text:
                    return (
                        task,
                        flame_controller,
                        spec_tel_mock,
                        file_builder_mock,
                        error_queue,
                    )
                await asyncio.sleep(start_poll_period)
            raise TimeoutError


def lists_equal(list1, list2):
    """
    Checks if two lists are equal
    """
    if len(list1) != len(list2):
        return False
    return all(list1[i] == list2[i] for i in range(len(list1)))


@pytest.mark.asyncio
async def test_controller_and_mock_objects(loguru_caplog):
    """
    Test controller_and_mock_objects method is working
    """

    await controller_and_mock_objects(loguru_caplog)

    assert True


@pytest.mark.asyncio
async def test_connection(loguru_caplog):
    """
    Test connect method is called correctly on startup
    """

    (
        _,
        _,
        spec_tel_mock,
        _,
        _,
    ) = await controller_and_mock_objects(loguru_caplog)

    spec_tel_mock.connect.assert_called()


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
        _,
        spec_tel_mock,
        _,
        error_queue,
    ) = await controller_and_mock_objects(loguru_caplog, spec_tel_mock=spec_tel_mock)

    task_pointer.cancel()
    await asyncio.gather(task_pointer)

    assert isinstance(error_queue.pop(), UnexpectedResponseError)
