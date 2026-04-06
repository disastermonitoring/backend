from typing import Literal

from pydantic import BaseModel, Field

from src.disaster_response.contracts.events import Coordinate


class RagQuery(BaseModel):
    event_id: str
    disaster_type: str
    location: str
    summary: str
    keywords: list[str] = Field(default_factory=list)
    coordinate: Coordinate | None = None
    flood_detected: bool | None = None
    flood_seriousness: Literal["none", "low", "moderate", "high", "critical"] | None = None
    estimated_water_depth_ft: float | None = Field(default=None, ge=0.0)
    affected_areas: list[str] = Field(default_factory=list)
    humans_detected: int | None = Field(default=None, ge=0)


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
