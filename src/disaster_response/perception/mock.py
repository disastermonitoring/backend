from src.disaster_response.contracts.events import (
    Coordinate,
    FloodZone,
    HumanDetection,
    OpticalAnalysisResult,
    SarAnalysisResult,
    SensorFrame,
)
from src.disaster_response.perception.base import OpticalModelAdapter, SarModelAdapter


def _token_number(raw_value: str) -> int:
    return sum(ord(char) for char in raw_value)


class MockOpticalModelAdapter(OpticalModelAdapter):
    async def analyze(self, frame: SensorFrame) -> OpticalAnalysisResult:
        base = _token_number(frame.frame_id)
        humans_detected = (base % 4) + 1
        detections: list[HumanDetection] = []
        for index in range(humans_detected):
            detections.append(
                HumanDetection(
                    detection_id=f"{frame.frame_id}-human-{index}",
                    confidence=round(min(0.99, 0.65 + (index * 0.07)), 2),
                    coordinate=Coordinate(
                        lat=9.60 + (index * 0.001),
                        lon=76.53 + (index * 0.001),
                    ),
                    bbox_xyxy=(10.0 * (index + 1), 20.0, 40.0, 80.0),
                )
            )
        return OpticalAnalysisResult(
            event_id=frame.event_id,
            frame_id=frame.frame_id,
            humans_detected=humans_detected,
            detections=detections,
            confidence=0.86,
        )


class MockSarModelAdapter(SarModelAdapter):
    async def analyze(self, frame: SensorFrame) -> SarAnalysisResult:
        base = _token_number(frame.frame_id)
        seriousness_levels = ["low", "moderate", "high", "critical"]
        seriousness = seriousness_levels[base % len(seriousness_levels)]
        return SarAnalysisResult(
            event_id=frame.event_id,
            frame_id=frame.frame_id,
            flood_detected=True,
            confidence=0.91,
            seriousness=seriousness, # pyright: ignore[reportArgumentType]
            zones=[
                FloodZone(
                    label="Primary flood zone",
                    severity=seriousness, # pyright: ignore[reportArgumentType]
                    confidence=0.9,
                    centroid=Coordinate(lat=9.6053, lon=76.5386),
                )
            ],
        )
