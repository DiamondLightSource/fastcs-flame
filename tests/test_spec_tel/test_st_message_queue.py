import asyncio

import pytest
from test_st_common import start_connection
from test_st_integration_time import CHANGED_INTEGRATION_TIME

from common import lists_equal


@pytest.mark.asyncio
async def test_get_scan_data_then_get_integration_time():
    """
    Test calling get_integration_time() whilst waiting for a scan data response

    This should not cause either call to error
    Integration time should be responded to after scan data is returned
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):

        async def get_integration_time_coroutine():
            await asyncio.sleep(1)
            recieved_integration_time = await spec_tel_obj.get_integration_time()
            assert dummy_spec_obj.integration_time == recieved_integration_time

        get_integration_time_task = asyncio.create_task(
            get_integration_time_coroutine()
        )

        recieved_scan_data = await spec_tel_obj.get_last_scan()

        assert lists_equal(dummy_spec_obj.last_scan_data, recieved_scan_data)

        await asyncio.gather(get_integration_time_task)


@pytest.mark.asyncio
async def test_scan_then_get_scan_data():
    """
    Test calling get_last_scan_data() whilst a scan is in progress

    This should not cause either call to error
    The scan data returned from the second query should match the
    NEW scan data
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):
        new_scan_data = []

        async def get_last_scan_data_coroutine():
            await asyncio.sleep(1)
            recieved_scan_data = await spec_tel_obj.get_last_scan()
            assert recieved_scan_data == new_scan_data

        get_last_scan_data_task = asyncio.create_task(get_last_scan_data_coroutine())

        old_scan_data = dummy_spec_obj.last_scan_data

        recieved_scan_data = await spec_tel_obj.scan()

        assert not lists_equal(old_scan_data, recieved_scan_data)
        new_scan_data = dummy_spec_obj.last_scan_data

        await asyncio.gather(get_last_scan_data_task)


@pytest.mark.asyncio
async def test_scan_then_set_and_get_integration_time():
    """
    Test queueing both a set and a get on integration time

    The set request should run first
    The get request should return the NEW integration time value
    """
    async with start_connection() as (dummy_spec_obj, spec_tel_obj):

        async def set_integration_time_coroutine():
            await asyncio.sleep(1)
            await spec_tel_obj.set_integration_time(CHANGED_INTEGRATION_TIME)

        async def get_integration_time_coroutine():
            await asyncio.sleep(2)
            recieved_integration_time = await spec_tel_obj.get_integration_time()
            assert recieved_integration_time == CHANGED_INTEGRATION_TIME

        set_integration_time_task = asyncio.create_task(
            set_integration_time_coroutine()
        )
        get_integration_time_task = asyncio.create_task(
            get_integration_time_coroutine()
        )

        old_scan_data = dummy_spec_obj.last_scan_data
        recieved_scan_data = await spec_tel_obj.scan()

        assert not lists_equal(old_scan_data, recieved_scan_data)
        assert lists_equal(dummy_spec_obj.last_scan_data, recieved_scan_data)

        await asyncio.gather(set_integration_time_task, get_integration_time_task)
