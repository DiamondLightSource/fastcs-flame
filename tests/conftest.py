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
