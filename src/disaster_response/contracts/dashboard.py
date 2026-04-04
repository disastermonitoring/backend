from pydantic import BaseModel, Field


class ImpactZonePayload(BaseModel):
    level: str
    area: str
    color: str


class ResourcePayload(BaseModel):
    boats: int = Field(default=0, ge=0)
    helicopters: int = Field(default=0, ge=0)
    medical: int = Field(default=0, ge=0)
    shelters: int = Field(default=0, ge=0)


class DashboardPayload(BaseModel):
    disaster_type: str
    confidence: str
    location: str
    time: str
    flood_detected: bool
    event_id: str
    water_depth: str
    affected_areas: str
    bridge_status: str
    keywords: list[str]
    alerts: list[str]
    route_alert: str
    detections: list[str]
    impact_zones: list[ImpactZonePayload]
    road_status: str
    flood_spread: str
    resources: ResourcePayload
    rs_station: str
    rs_coords: str
    current_actions: list[str]
    ai_assessment: str
    recommended_resources: list[str]

