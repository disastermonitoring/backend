import asyncio

from disaster_response.contracts.events import SensorFrame
from disaster_response.ingestion.base import SensorStreamSource


class InMemorySensorStream(SensorStreamSource):
    def __init__(self) -> None:
        self._queue: asyncio.Queue[SensorFrame] = asyncio.Queue()

    async def push(self, frame: SensorFrame) -> None:
        await self._queue.put(frame)

    async def read(self) -> SensorFrame:
        return await self._queue.get()
