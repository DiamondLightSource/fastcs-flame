import asyncio

import pytest
from fastcs.launch import FastCS
from fastcs.logging import configure_logging

from dummy_spectrometer import DummySpectrometer
from fastcsflame.flame_controller import FlameController
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


def replace_spec_tel_methods(spec_tel: SpecTel):
    # This feels like a really bad way to do it
    # But we cant replace the object in the controller
    # as the attributes have stored a reference
    # We need to modify the existing object instead
    # Maybe this indicates the controller is not designed very well :(
    connected_pointer = [False]
    spectrometer = DummySpectrometer(spec_tel.port, bind=False)

    def connect():
        if connected_pointer[0]:
            # TOOD: Add exception for this (to actual class too)
            print("already connected")
        connected_pointer[0] = True

    def get_version() -> int:
        return spectrometer.version

    def get_integration_time() -> int:
        return spectrometer.integration_time

    def set_integration_time(integration_time):
        spectrometer.integration_time = integration_time

    def get_last_scan() -> list[int]:
        return spectrometer.last_scan_data

    def scan() -> list[int]:
        spectrometer.randomise_scan_data()
        return spectrometer.last_scan_data

    spec_tel.connect = connect
    spec_tel.get_version = get_version
    spec_tel.get_integration_time = get_integration_time
    spec_tel.set_integration_time = set_integration_time
    spec_tel.get_last_scan = get_last_scan
    spec_tel.scan = scan

    return (connected_pointer, spectrometer)


async def controller_spectrometer_and_connected_pointer():
    configure_logging()

    flame_controller = FlameController(
        "172.23.91.5", 7016, default_nexus_save_file_path="./data.txt"
    )
    connected_pointer, spectrometer = replace_spec_tel_methods(
        flame_controller.spec_tel_obj
    )
    flame_controller.set_path(["FLAME"])
    fastcs = FastCS(flame_controller, [])

    asyncio.create_task(fastcs.serve(interactive=False))

    # give fastcs some time to set up
    # theres probably a callback for when this finishes??
    # TODO: use a more precise method of waiting
    await asyncio.sleep(3)

    return (flame_controller, spectrometer, connected_pointer)


def lists_equal(list1, list2):
    if len(list1) != len(list2):
        return False
    return all(list1[i] == list2[i] for i in range(len(list1)))


@pytest.mark.asyncio
async def test_controller_initialisation():

    (
        flame_controller,
        spectrometer,
        connected_pointer,
    ) = await controller_spectrometer_and_connected_pointer()

    assert connected_pointer[0]
    assert flame_controller.integration_time.get() == spectrometer.integration_time
    assert lists_equal(flame_controller.scan_data.get(), spectrometer.last_scan_data)


@pytest.mark.asyncio
async def test_caput_integration_time():
    (
        flame_controller,
        spectrometer,
        _,
    ) = await controller_spectrometer_and_connected_pointer()

    new_integration_time = spectrometer.integration_time + 1
    await flame_controller.integration_time.put(new_integration_time)
    assert spectrometer.integration_time == new_integration_time
