import asyncio

import pytest

from src.disaster_response.contracts.incident import FieldAcknowledgement, IncidentState, SOSMessage
from src.disaster_response.planning.service import PlanningService
from src.disaster_response.rag.base import RagProvider

@pytest.fixture(scope="session")
def rag_provider() -> RagProvider:
    from src.main import _build_rag_provider
    provider = _build_rag_provider()
    return provider


@pytest.mark.asyncio
async def test_planning_service_refresh_prints_outputs(rag_provider: RagProvider) -> None:
    """Run with `pytest -s` to print computed planning state."""

    async def scenario() -> IncidentState:
        planning = PlanningService(rag_provider=rag_provider)
        incident = IncidentState(
            event_id="evt-plan-print-001",
            location_name="Kottayam, Kerala",
            location="Kottayam, Kerala",
        )

        incident.sar.last_frame_id = "sar-001"
        incident.sar.flood_detected = True
        incident.sar.seriousness = "high"
        incident.sar.confidence = 0.91
        incident.sar.affected_areas = ["Athirampuzha"]
        incident.sar.blocked_routes = ["NH-183"]
        incident.sar.bridge_status = "Bridge Unsafe"
        incident.sar.estimated_water_depth_ft = 3.8

        incident.optical.humans_detected = 4
        incident.optical.confidence = 0.88

        incident.sos_messages.append(
            SOSMessage(
                source="sms",
                sender="citizen-1",
                message="Water rising fast near school roof",
                credibility_score=0.84,
            )
        )
        incident.field_acknowledgements.append(
            FieldAcknowledgement(
                team_id="team-3",
                status="confirmed",
                message="Road partially submerged, bridge access restricted",
                location_hint="NH-183",
            )
        )

        refreshed = await planning.refresh(incident)
        return refreshed

    result = await scenario()

    print("\n=== PLANNING SERVICE OUTPUT ===")
    print("Event:", result.event_id)
    print("Threat priority:", result.planning.threat_priority)
    print("Flood seriousness:", result.flood_seriousness)
    print("Route alert:", result.route_alert)
    print("AI assessment:", result.ai_assessment)
    print("Recommended resources:", result.recommended_resources)
    print("Current actions:", result.current_actions)
    print("RAG summary:", result.rag_summary)
    print("RAG context titles:", result.rag_context_titles)
    print("Planning recommended actions:", result.planning.recommended_actions)

    assert result.planning.threat_priority in {"P1", "P2", "P3"}
    assert result.ai_assessment
    assert len(result.current_actions) > 0
    assert len(result.recommended_resources) > 0
