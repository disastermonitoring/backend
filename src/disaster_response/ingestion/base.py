from abc import ABC, abstractmethod

from src.disaster_response.contracts.events import SensorFrame


class SensorStreamSource(ABC):
    """Abstraction for continuous sensor streams."""

    @abstractmethod
    async def push(self, frame: SensorFrame) -> None:
        """Push a frame into the stream."""

    @abstractmethod
    async def read(self) -> SensorFrame:
        """Read the next frame from the stream."""
