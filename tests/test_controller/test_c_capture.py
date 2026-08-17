import pytest
from test_c_common import controller_and_mock_objects

DUMMY_FILE_PATH_1 = "/scratch/wvq67617/files"
DUMMY_FILE_NAME_1 = "data"
DUMMY_FILE_PATH_2 = "./data"
DUMMY_FILE_NAME_2 = "collection_1"


@pytest.mark.asyncio
async def test_file_builder(loguru_caplog):
    """
    Tests file builder method calls on capture switch with varying paths and names
    """

    (
        _,
        flame_controller,
        _,
        file_builder_mock,
        _,
    ) = await controller_and_mock_objects(loguru_caplog)

    await flame_controller.file_path.put(DUMMY_FILE_PATH_1)
    await flame_controller.file_name.put(DUMMY_FILE_NAME_1)

    await flame_controller.capture.put(True)

    # Check setting capture to true called create_file with file params
    file_builder_mock.create_file.assert_called_once_with(
        DUMMY_FILE_PATH_1, DUMMY_FILE_NAME_1
    )

    scans = 10
    for _ in range(scans):
        await flame_controller.single_scan()
    # Check add_scan was called once for each scan
    assert file_builder_mock.add_scan.call_count == scans

    await flame_controller.capture.put(False)

    file_builder_mock.close_file.assert_called_once()

    await flame_controller.single_scan()
    # Check add scan was not called again since capture is false
    assert file_builder_mock.add_scan.call_count == scans

    await flame_controller.file_path.put(DUMMY_FILE_PATH_2)
    await flame_controller.file_name.put(DUMMY_FILE_NAME_2)
    await flame_controller.capture.put(True)

    # Check file will be created in a new location when  capture starts again
    file_builder_mock.create_file.assert_called_with(
        DUMMY_FILE_PATH_2, DUMMY_FILE_NAME_2
    )
