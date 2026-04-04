from abc import ABC, abstractmethod


class SOSCommunicationChannel(ABC):
    @abstractmethod
    async def send_message(self, recipient: str, message: str) -> None:
        """Send an SOS-related message through a provider-specific channel."""

