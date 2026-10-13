"""Run async tests reliably on runtimes that miss executor wakeups."""

import asyncio
from collections.abc import Awaitable
from typing import TypeVar


T = TypeVar("T")


def run_async(awaitable: Awaitable[T]) -> T:
    async def runner() -> T:
        # This test environment's Python 3.14 loop can miss the wakeup sent
        # when a thread-pool job completes. A pending timer keeps it polling.
        async def wake_loop() -> None:
            while True:
                await asyncio.sleep(0.01)

        heartbeat = asyncio.create_task(wake_loop())
        try:
            return await awaitable
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass

    return asyncio.run(runner())
