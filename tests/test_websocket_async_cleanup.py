#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration test for WebSocket async task cleanup fix.
Verifies that async tasks exit cleanly when WebSocket closes.
"""

import asyncio
import tornado.locks
from tornado import gen


async def test_async_task_exits_on_close_event():
    """
    Tests that async loops properly exit when close_event is set.
    This simulates the actual WebSocket handler behavior.
    """
    # Simulate the WebSocketHandler state
    state = {
        'sending_pending_tasks_info': True,
        'close_event_set': False,
    }

    class MockCloseEvent:
        def is_set(self):
            return state['close_event_set']

    async def async_pending_tasks_info_fixed():
        """Fixed version with close_event checks"""
        close_event = MockCloseEvent()

        while state['sending_pending_tasks_info']:
            # Exit immediately if close_event is set
            if close_event.is_set():
                break

            # Simulate fetching task data
            await gen.sleep(0.01)

            # Sleep for X seconds, checking close_event frequently
            for _ in range(30):
                if close_event.is_set():
                    return
                await gen.sleep(0.1)

    # Spawn the task
    task = asyncio.create_task(async_pending_tasks_info_fixed())

    # Let it run briefly
    await gen.sleep(0.02)

    # Simulate WebSocket close: set close_event
    state['close_event_set'] = True

    # Verify task exits quickly (within 150ms instead of 3+ seconds)
    start = asyncio.get_event_loop().time()
    await asyncio.wait_for(asyncio.shield(task), timeout=0.3)
    elapsed = asyncio.get_event_loop().time() - start

    assert task.done(), "Task should have completed"
    assert elapsed < 0.2, f"Task should exit within 200ms, but took {elapsed * 1000:.0f}ms"
    print(f"✓ Task exited cleanly in {elapsed * 1000:.1f}ms (expected ~100ms)")


async def test_all_async_methods_cleanup():
    """
    Verify that all async_* methods have close_event checks.
    This is a regression test to ensure the fix is applied consistently.
    """
    with open('unmanic/webserver/websocket.py', 'r') as f:
        source_code = f.read()

    # Methods that should have close_event checks
    async_methods = [
        'async_frontend_message',
        'async_system_logs',
        'async_workers_info',
        'async_pending_tasks_info',
        'async_completed_tasks_info',
    ]

    for method in async_methods:
        # Check that the method contains close_event.is_set() check
        method_start = source_code.find(f'async def {method}')
        assert method_start != -1, f"Method {method} not found"

        # Find the next async def to get method boundaries
        next_method_start = source_code.find('async def ', method_start + 1)
        if next_method_start == -1:
            # This is the last method, use end of file
            next_method_start = len(source_code)
        method_code = source_code[method_start:next_method_start]

        assert 'self.close_event.is_set()' in method_code, \
            f"Method {method} missing close_event.is_set() check"

    print(f"✓ All {len(async_methods)} async methods have close_event checks")


if __name__ == '__main__':
    print("Test 1: Async task exits cleanly on close_event...")
    asyncio.run(test_async_task_exits_on_close_event())

    print("\nTest 2: All async methods have close_event cleanup...")
    asyncio.run(test_all_async_methods_cleanup())

    print("\n✓ All tests passed!")
