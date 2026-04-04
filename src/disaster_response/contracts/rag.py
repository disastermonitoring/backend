from pydantic import BaseModel, Field


class RagQuery(BaseModel):
    event_id: str
    disaster_type: str
    location: str
    summary: str
    keywords: list[str] = Field(default_factory=list)


class RagContextItem(BaseModel):
    source_type: str
    title: str
    content: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class RagResult(BaseModel):
    event_id: str
    summary: str
    recommended_actions: list[str] = Field(default_factory=list)
    context_items: list[RagContextItem] = Field(default_factory=list)

