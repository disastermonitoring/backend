from abc import ABC, abstractmethod

from disaster_response.contracts.rag import RagQuery, RagResult


class RagProvider(ABC):
    """Abstraction boundary for the separately implemented RAG module."""

    @abstractmethod
    async def enrich(self, query: RagQuery) -> RagResult:
        """Return contextual information and recommendations for an event."""

