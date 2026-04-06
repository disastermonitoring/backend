from src.disaster_response.communications.base import SOSCommunicationChannel
from src.disaster_response.core.logging_config import get_logger


class LoggingSOSChannel(SOSCommunicationChannel):
    def __init__(self, channel_name: str) -> None:
        self.channel_name = channel_name
        self.logger = get_logger("disaster_response.communications")

    async def send_message(self, recipient: str, message: str) -> None:
        self.logger.info(
            "outbound_sos_message channel=%s recipient=%s message=%s",
            self.channel_name,
            recipient,
            message,
        )
