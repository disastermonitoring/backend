from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SensorType = Literal["optical", "sar"]


class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class SensorFrame(BaseModel):
    event_id: str
    sensor_type: SensorType
    frame_id: str
    captured_at: datetime
    source_id: str
    payload_uri: str
    location_name: str | None = None
    coordinate: Coordinate | None = None


class HumanDetection(BaseModel):
    detection_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    coordinate: Coordinate | None = None
    bbox_xyxy: tuple[float, float, float, float] | None = None


class OpticalAnalysisResult(BaseModel):
    event_id: str
    frame_id: str
    humans_detected: int = Field(..., ge=0)
    detections: list[HumanDetection] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class FloodZone(BaseModel):
    label: str
    severity: Literal["low", "moderate", "high", "critical"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    centroid: Coordinate | None = None


class SarAnalysisResult(BaseModel):
    event_id: str
    frame_id: str
    flood_detected: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    seriousness: Literal["none", "low", "moderate", "high", "critical"]
    zones: list[FloodZone] = Field(default_factory=list)
    estimated_water_depth_ft: float | None = Field(default=None, ge=0.0)
    affected_areas: list[str] = Field(default_factory=list)
    blocked_routes: list[str] = Field(default_factory=list)
    bridge_status: str | None = None
    detected_structures: list[str] = Field(default_factory=list)
