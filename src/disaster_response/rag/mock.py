from disaster_response.contracts.rag import RagQuery, RagResult
from disaster_response.rag.base import RagProvider


class NullRagProvider(RagProvider):
    """Safe default provider until the real RAG module is wired in."""

    async def enrich(self, query: RagQuery) -> RagResult:
        return RagResult(
            event_id=query.event_id,
            summary="RAG provider not configured.",
            recommended_actions=[],
            context_items=[],
        )

