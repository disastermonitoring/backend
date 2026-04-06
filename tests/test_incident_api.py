import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.disaster_response.communications.mock import LoggingSOSChannel  # noqa: E402
from src.disaster_response.contracts.events import Coordinate, FloodZone, OpticalAnalysisResult, SarAnalysisResult  # noqa: E402
from src.disaster_response.contracts.incident import FieldAcknowledgement, SOSMessage  # noqa: E402
from src.disaster_response.contracts.rag import RagContextItem, RagResult  # noqa: E402
from src.disaster_response.perception.mock import MockOpticalModelAdapter, MockSarModelAdapter  # noqa: E402
from src.disaster_response.planning.service import PlanningService  # noqa: E402
from src.disaster_response.projection.dashboard import DashboardProjector  # noqa: E402
from src.disaster_response.rag.mock import NullRagProvider  # noqa: E402
from src.disaster_response.services.incidents import IncidentService  # noqa: E402
from src.disaster_response.state.store import InMemoryIncidentStore  # noqa: E402


def build_service() -> IncidentService:
    rag_provider = NullRagProvider()
    return IncidentService(
        store=InMemoryIncidentStore(),
        rag_provider=rag_provider,
        optical_adapter=MockOpticalModelAdapter(),
        sar_adapter=MockSarModelAdapter(),
        planner=PlanningService(rag_provider=rag_provider),
        projector=DashboardProjector(),
        communication_channels={
            "sms": LoggingSOSChannel("sms"),
            "whatsapp": LoggingSOSChannel("whatsapp"),
        },
    )


def test_event_lifecycle_end_to_end() -> None:
    async def scenario() -> None:
        service = build_service()
        event_id = "evt-demo-001"

        await service.record_optical_analysis(
            OpticalAnalysisResult(
                event_id=event_id,
                frame_id="optical-001",
                humans_detected=3,
                detections=[],
                confidence=0.88,
            )
        )
        await service.record_sar_analysis(
            SarAnalysisResult(
                event_id=event_id,
                frame_id="sar-001",
                flood_detected=True,
                confidence=0.94,
                seriousness="high",
                zones=[
                    FloodZone(
                        label="Kottayam District",
                        severity="high",
                        confidence=0.92,
                        centroid=Coordinate(lat=9.6053, lon=76.5386),
                    )
                ],
            )
        )
        await service.record_sos_message(
            event_id,
            SOSMessage(
                source="sms",
                sender="Kottayam Boat Launch",
                message="Family trapped on rooftop, water rising",
                credibility_score=0.81,
                coordinate=Coordinate(lat=9.6051, lon=76.5388),
            ),
        )
        await service.record_field_acknowledgement(
            event_id,
            FieldAcknowledgement(
                team_id="team-7",
                status="blocked",
                message="Bridge over NH-183 is not traversable",
                location_hint="NH-183",
            ),
        )
        await service.record_rag_result(
            RagResult(
                event_id=event_id,
                summary="Severe flood with trapped civilians; prioritize boat rescue and route diversion.",
                recommended_actions=["ImmediateBoatRescue", "PowerGridShutdown"],
                context_items=[
                    RagContextItem(
                        source_type="sop",
                        title="Kerala flood SOP",
                        content="Prioritize water rescue and establish diversion routes.",
                        relevance_score=0.95,
                    )
                ],
            )
        )

        payload = await service.get_dashboard_payload(event_id)
        assert payload.flood_detected is True
        assert payload.bridge_status == "Bridge Unsafe, Access Restricted"
        assert "People Seen" in payload.detections
        assert "Family trapped on rooftop, water rising" in payload.alerts
        assert "Boat" in payload.recommended_resources
        assert payload.ai_assessment.startswith("Severe flood with trapped civilians")

    asyncio.run(scenario())


def test_mock_frame_ingestion() -> None:
    async def scenario() -> None:
        service = build_service()
        incident = await service.ingest_optical_frame(
            frame=type("Frame", (), {
                "event_id": "evt-demo-002",
                "sensor_type": "optical",
                "frame_id": "frame-42",
                "captured_at": None,
                "source_id": "drone-optical-1",
                "payload_uri": "file:///tmp/optical-42.png",
            })()
        )
        assert incident.latest_optical_analysis is not None
        assert incident.latest_optical_analysis.humans_detected >= 1

    asyncio.run(scenario())
