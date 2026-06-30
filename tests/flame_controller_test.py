import asyncio
from datetime import datetime as dt

import numpy as np
import pytest
from fastcs.launch import FastCS
from fastcs.logging import configure_logging

from dummy_hdf5_file_builder import DummyHdf5FileBuilder
from dummy_spectrometer import DummySpectrometer
from fastcsflame.flame_controller import SCAN_DATA_LENGTH, FlameController
from fastcsflame.spectrometer_telecommunicator import (
    AlreadyConnectedError,
    UnexpectedResponseError,
)


def replace_controllers_spec_tel_methods(
    flame_controller: FlameController,
    error_connect=False,
    error_version=False,
    error_get_integration_time=False,
    error_set_integration_time=False,
    error_get_last_scan=False,
    error_scan=False,
):
    # Cant replace the controllers spec_tel object directly as a lot of the
    # Refs have a pointer to the old one
    # This makes sense as the controller composes? the tel_spec
    # However, this means its really tricky to mock the tel_spec object
    # The best way I could think of doing it is replacing all methods
    # This means we dont have to properly connect the spec_tel and spectrometer
    spec_tel = flame_controller.spec_tel_obj
    spectrometer = DummySpectrometer(spec_tel.port, bind=False)

    def connect():
        if error_connect:
            raise UnexpectedResponseError()
        if spec_tel.connected:
            raise AlreadyConnectedError
        spec_tel.connected = True

    def get_version() -> int:
        if error_version:
            raise UnexpectedResponseError()
        return spectrometer.version

    def get_integration_time() -> int:
        if error_get_integration_time:
            raise UnexpectedResponseError()
        return spectrometer.integration_time

    def set_integration_time(integration_time):
        if error_set_integration_time:
            raise UnexpectedResponseError()
        spectrometer.integration_time = integration_time

    def get_last_scan() -> list[int]:
        if error_get_last_scan:
            raise UnexpectedResponseError()
        return spectrometer.last_scan_data

    def scan() -> list[int]:
        if error_scan:
            raise UnexpectedResponseError()
        spectrometer.randomise_scan_data()
        return spectrometer.last_scan_data

    spec_tel.connect = connect
    spec_tel.get_version = get_version
    spec_tel.get_integration_time = get_integration_time
    spec_tel.set_integration_time = set_integration_time
    spec_tel.get_last_scan = get_last_scan
    spec_tel.scan = scan

    return spectrometer


async def controller_ang_spectrometer(**kwargs):
    configure_logging()

    flame_controller = FlameController(
        "172.23.91.5", 7016, default_nexus_save_file_path="./data.txt"
    )
    spectrometer = replace_controllers_spec_tel_methods(flame_controller, **kwargs)
    flame_controller.set_path(["FLAME"])
    fastcs = FastCS(flame_controller, [])

    asyncio.create_task(fastcs.serve(interactive=False))

    # give fastcs some time to set up
    # theres probably a callback for when this finishes??
    # TODO: use a more precise method of waiting
    await asyncio.sleep(3)

    return flame_controller, spectrometer


def lists_equal(list1, list2):
    if len(list1) != len(list2):
        return False
    return all(list1[i] == list2[i] for i in range(len(list1)))


@pytest.mark.asyncio
async def test_controller_initialisation():

    (
        flame_controller,
        spectrometer,
    ) = await controller_ang_spectrometer()

    assert flame_controller.spec_tel_obj.connected
    assert flame_controller.integration_time.get() == spectrometer.integration_time
    assert lists_equal(flame_controller.scan_data.get(), spectrometer.last_scan_data)


@pytest.mark.asyncio
async def test_caput_integration_time():
    (
        flame_controller,
        spectrometer,
    ) = await controller_ang_spectrometer()

    new_integration_time = spectrometer.integration_time + 1
    await flame_controller.integration_time.put(new_integration_time)
    assert spectrometer.integration_time == new_integration_time


@pytest.mark.asyncio
async def test_scan_data_command():
    flame_controller, spectrometer = await controller_ang_spectrometer()

    old_scan_data = flame_controller.scan_data.get()
    await flame_controller.single_scan()
    new_scan_data = flame_controller.scan_data.get()

    assert not lists_equal(old_scan_data, new_scan_data)
    assert lists_equal(spectrometer.last_scan_data, new_scan_data)


@pytest.mark.asyncio
async def test_acquire_data_timings():
    flame_controller, _ = await controller_ang_spectrometer()

    dummy_fb = flame_controller.file_builder = DummyHdf5FileBuilder()

    scan_start = np.datetime64(dt.now())

    await flame_controller.acquire_data()

    scan_end = np.datetime64(dt.now())

    assert dummy_fb.create_h5_file_times_arg is not None
    assert len(dummy_fb.create_h5_file_times_arg.shape) == 1
    assert (
        dummy_fb.create_h5_file_times_arg.shape[0] == flame_controller.total_scans.get()
    )
    assert np.datetime64(scan_start) < dummy_fb.create_h5_file_times_arg[0]
    assert dummy_fb.create_h5_file_times_arg[-1] < np.datetime64(scan_end)
    scan_period = (
        dummy_fb.create_h5_file_times_arg[-1] - dummy_fb.create_h5_file_times_arg[0]
    )
    assert (
        flame_controller.acquisition_period.get() - 1
        < scan_period.item().total_seconds()
        and scan_period.item().total_seconds()
        < flame_controller.acquisition_period.get() + 1
    )


@pytest.mark.asyncio
async def test_acquire_data_timings_after_set():
    flame_controller, _ = await controller_ang_spectrometer()

    await flame_controller.acquisition_period.put(
        flame_controller.acquisition_period.get() * 2
    )
    await flame_controller.total_scans.put(
        int(flame_controller.total_scans.get() * 2 / 3)
    )

    dummy_fb = flame_controller.file_builder = DummyHdf5FileBuilder()

    scan_start = np.datetime64(dt.now())

    await flame_controller.acquire_data()

    scan_end = np.datetime64(dt.now())

    assert dummy_fb.create_h5_file_times_arg is not None
    assert len(dummy_fb.create_h5_file_times_arg.shape) == 1
    assert (
        dummy_fb.create_h5_file_times_arg.shape[0] == flame_controller.total_scans.get()
    )
    assert np.datetime64(scan_start) < dummy_fb.create_h5_file_times_arg[0]
    assert dummy_fb.create_h5_file_times_arg[-1] < np.datetime64(scan_end)
    scan_period = (
        dummy_fb.create_h5_file_times_arg[-1] - dummy_fb.create_h5_file_times_arg[0]
    )
    assert (
        flame_controller.acquisition_period.get() - 1
        < scan_period.item().total_seconds()
        and scan_period.item().total_seconds()
        < flame_controller.acquisition_period.get() + 1
    )


@pytest.mark.asyncio
async def test_create_file_call():
    flame_controller, _ = await controller_ang_spectrometer()

    dummy_fb = flame_controller.file_builder = DummyHdf5FileBuilder()

    scan_start = np.datetime64(dt.now())

    await flame_controller.acquire_data()

    scan_end = np.datetime64(dt.now())

    assert (
        dummy_fb.create_h5_file_destination_arg
        == flame_controller.nexus_save_file_path.get()
    )
    assert (
        dummy_fb.create_h5_file_filename_arg
        == flame_controller.nexus_save_file_name.get()
    )
    assert dummy_fb.create_h5_file_title_arg == flame_controller.title.get()
    assert dummy_fb.create_h5_file_sample_name_arg == flame_controller.sample_name.get()
    assert dummy_fb.create_h5_file_sample_id_arg == flame_controller.sample_id.get()

    assert dummy_fb.create_h5_file_data_arg is not None
    assert (
        dummy_fb.create_h5_file_data_arg.shape[0] == flame_controller.total_scans.get()
    )
    assert dummy_fb.create_h5_file_data_arg.shape[1] == SCAN_DATA_LENGTH

    assert dummy_fb.create_h5_file_times_arg is not None
    assert (
        dummy_fb.create_h5_file_times_arg.shape[0] == flame_controller.total_scans.get()
    )
    assert all(
        scan_start < time and time < scan_end
        for time in dummy_fb.create_h5_file_times_arg
    )


# TODO: Test exceptions are raised correctly
# This is quite tricky as FastCS handles and logs them
# Will need to check logs instead??
