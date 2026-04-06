from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.disaster_response.contracts.dashboard import ResourcePayload
from src.disaster_response.contracts.events import (
    Coordinate,
    FloodZone,
    HumanDetection,
    OpticalAnalysisResult,
    SarAnalysisResult,
)
from src.disaster_response.contracts.rag import RagResult


ThreatPriority = Literal["P1", "P2", "P3"]
FieldStatus = Literal["received", "confirmed", "needs_update", "resolved", "in_progress", "blocked"]


class SOSMessage(BaseModel):
    source: Literal["sms", "whatsapp", "manual"]
    sender: str
    message: str
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    coordinate: Coordinate | None = None


SOSReport = SOSMessage


class FieldAcknowledgement(BaseModel):
    troop_id: str | None = None
    team_id: str | None = None
    status: FieldStatus
    note: str = ""
    message: str = ""
    confirmed_hazards: list[str] = Field(default_factory=list)
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    acknowledged_at: datetime | None = None
    location_hint: str | None = None

    def model_post_init(self, __context) -> None:
        if self.troop_id is None and self.team_id is not None:
            self.troop_id = self.team_id
        if self.team_id is None and self.troop_id is not None:
            self.team_id = self.troop_id
        if not self.note and self.message:
            self.note = self.message
        if not self.message and self.note:
            self.message = self.note
        if self.acknowledged_at is None:
            self.acknowledged_at = self.received_at


class DispatchedMessage(BaseModel):
    channel: Literal["sms", "whatsapp"]
    recipient: str
    message: str
    sent_at: datetime
    status: Literal["queued", "sent"] = "sent"


class OpticalPerceptionState(BaseModel):
    last_frame_id: str | None = None
    humans_detected: int = 0
    detections: list[HumanDetection] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated: datetime | None = None


class SarPerceptionState(BaseModel):
    last_frame_id: str | None = None
    flood_detected: bool = False
    seriousness: Literal["none", "low", "moderate", "high", "critical"] = "none"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    zones: list[FloodZone] = Field(default_factory=list)
    estimated_water_depth_ft: float | None = None
    affected_areas: list[str] = Field(default_factory=list)
    blocked_routes: list[str] = Field(default_factory=list)
    bridge_status: str | None = None
    last_updated: datetime | None = None


class PlanningState(BaseModel):
    threat_priority: ThreatPriority = "P3"
    keywords: list[str] = Field(default_factory=list)
    current_actions: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    recommended_resources: list[str] = Field(default_factory=list)
    resources: ResourcePayload = Field(default_factory=ResourcePayload)
    route_alert: str = "No route restrictions recorded"
    ai_assessment: str = "Awaiting enough sensor evidence to assess the incident."
    rescue_station: str = "Unknown"
    rescue_coordinates: str = ""
    updated_at: datetime | None = None


class IncidentState(BaseModel):
    event_id: str
    disaster_type: str = "Flood"
    location_name: str = "Unknown"
    location: str = "Unknown"
    coordinate: Coordinate | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    flood_detected: bool = False
    flood_seriousness: Literal["none", "low", "moderate", "high", "critical"] = "none"
    affected_areas: list[str] = Field(default_factory=list)
    latest_optical_analysis: OpticalAnalysisResult | None = None
    latest_sar_analysis: SarAnalysisResult | None = None
    optical: OpticalPerceptionState = Field(default_factory=OpticalPerceptionState)
    sar: SarPerceptionState = Field(default_factory=SarPerceptionState)
    sos_messages: list[SOSMessage] = Field(default_factory=list)
    sos_reports: list[SOSReport] = Field(default_factory=list)
    rag_result: RagResult | None = None
    rag_summary: str | None = None
    rag_context_titles: list[str] = Field(default_factory=list)
    rag_recommended_actions: list[str] = Field(default_factory=list)
    field_acknowledgements: list[FieldAcknowledgement] = Field(default_factory=list)
    dispatched_messages: list[DispatchedMessage] = Field(default_factory=list)
    detections: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    current_actions: list[str] = Field(default_factory=list)
    recommended_resources: list[str] = Field(default_factory=list)
    resources: ResourcePayload = Field(default_factory=ResourcePayload)
    water_depth: str = "Unknown"
    bridge_status: str = "Unknown"
    route_alert: str = "No routing alert"
    road_status: str = "Unknown"
    flood_spread: str = "Unknown"
    impact_zones: list[dict[str, str]] = Field(default_factory=list)
    ai_assessment: str = "No assessment available yet."
    rs_station: str = "Unknown"
    rs_coords: str = "Unknown"
    planning: PlanningState = Field(default_factory=PlanningState)
    audit_notes: list[str] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        if self.location_name == "Unknown" and self.location != "Unknown":
            self.location_name = self.location
        if self.location == "Unknown" and self.location_name != "Unknown":
            self.location = self.location_name
