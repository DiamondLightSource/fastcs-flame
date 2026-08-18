from collections.abc import Generator

import pytest
from fastcs.logging import configure_logging, logger
from pytest import LogCaptureFixture


@pytest.fixture
def loguru_caplog(caplog) -> Generator[LogCaptureFixture]:
    """
    Suggested FastCS fixture for capturing log output of a controller
    """
    configure_logging()
    handler_id = logger.add(caplog.handler, format="{message}", level="TRACE")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture(params=[0, 1, 2, 3])
def wcc_details(request):

    order = request.param
    default_values: dict[int, float] = {
        1: 178.89592,
        2: 0.38649029,
        3: -0.000018147914,
        4: -0.000000020812843,
    }
    change_values: dict[int, float] = {
        1: 179.89592,
        2: 0.39649029,
        3: -0.000019147914,
        4: -0.000000021812843,
    }

    return (order, default_values[order + 1], change_values[order + 1])
