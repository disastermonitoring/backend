from datetime import UTC, datetime

from src.disaster_response.communications.base import SOSCommunicationChannel
from src.disaster_response.contracts.dashboard import DashboardPayload
from src.disaster_response.contracts.events import OpticalAnalysisResult, SarAnalysisResult, SensorFrame
from src.disaster_response.contracts.incident import FieldAcknowledgement, IncidentState, SOSMessage
from src.disaster_response.contracts.rag import RagQuery, RagResult
from src.disaster_response.core.logging_config import get_logger
from src.disaster_response.perception.base import OpticalModelAdapter, SarModelAdapter
from src.disaster_response.planning.service import PlanningService
from src.disaster_response.projection.dashboard import DashboardProjector
from src.disaster_response.rag.base import RagProvider
from src.disaster_response.state.store import InMemoryIncidentStore


class IncidentService:
    def __init__(
        self,
        store: InMemoryIncidentStore,
        rag_provider: RagProvider,
        optical_adapter: OpticalModelAdapter,
        sar_adapter: SarModelAdapter,
        planner: PlanningService,
        projector: DashboardProjector,
        communication_channels: dict[str, SOSCommunicationChannel],
    ) -> None:
        self.store = store
        self.rag_provider = rag_provider
        self.optical_adapter = optical_adapter
        self.sar_adapter = sar_adapter
        self.planner = planner
        self.projector = projector
        self.communication_channels = communication_channels
        self.app_logger = get_logger("disaster_response")
        self.model_logger = get_logger("disaster_response.models")
        self.decision_logger = get_logger("disaster_response.decisions")
        self.field_logger = get_logger("disaster_response.field")

    async def _get_or_create(self, event_id: str) -> IncidentState:
        incident = await self.store.get(event_id)
        if incident is not None:
            return incident
        incident = IncidentState(event_id=event_id)
        await self.store.upsert(incident)
        return incident

    async def ingest_optical_frame(self, frame: SensorFrame) -> IncidentState:
        self.model_logger.info("optical_frame_received event_id=%s frame_id=%s", frame.event_id, frame.frame_id)
        result = await self.optical_adapter.analyze(frame)
        self.model_logger.info(
            "optical_analysis_completed event_id=%s humans=%s",
            result.event_id,
            result.humans_detected,
        )
        incident = await self.record_optical_analysis(result)
        self._apply_frame_context(incident, frame)
        await self.store.upsert(incident)
        return incident

    async def ingest_sar_frame(self, frame: SensorFrame) -> IncidentState:
        self.model_logger.info("sar_frame_received event_id=%s frame_id=%s", frame.event_id, frame.frame_id)
        result = await self.sar_adapter.analyze(frame)
        self.model_logger.info(
            "sar_analysis_completed event_id=%s seriousness=%s",
            result.event_id,
            result.seriousness,
        )
        incident = await self.record_sar_analysis(result)
        self._apply_frame_context(incident, frame)
        await self.store.upsert(incident)
        return incident

    async def record_optical_analysis(self, result: OpticalAnalysisResult) -> IncidentState:
        incident = await self._get_or_create(result.event_id)
        incident.latest_optical_analysis = result
        incident.optical.last_frame_id = result.frame_id
        incident.optical.humans_detected = result.humans_detected
        incident.optical.detections = result.detections
        incident.optical.confidence = result.confidence
        incident.optical.last_updated = datetime.now(UTC)
        incident.confidence = max(incident.confidence, result.confidence)
        incident.updated_at = datetime.now(UTC)
        incident.version += 1
        incident = self.planner.recompute(incident)
        await self.store.upsert(incident)
        self.decision_logger.info(
            "incident_updated_from_optical event_id=%s version=%s",
            incident.event_id,
            incident.version,
        )
        return incident

    async def record_sar_analysis(self, result: SarAnalysisResult) -> IncidentState:
        incident = await self._get_or_create(result.event_id)
        incident.latest_sar_analysis = result
        incident.sar.last_frame_id = result.frame_id
        incident.sar.flood_detected = result.flood_detected
        incident.sar.seriousness = result.seriousness
        incident.sar.confidence = result.confidence
        incident.sar.zones = result.zones
        incident.sar.estimated_water_depth_ft = result.estimated_water_depth_ft
        incident.sar.affected_areas = result.affected_areas
        incident.sar.blocked_routes = result.blocked_routes
        incident.sar.bridge_status = result.bridge_status
        incident.sar.last_updated = datetime.now(UTC)
        incident.flood_detected = result.flood_detected
        incident.flood_seriousness = result.seriousness
        incident.confidence = max(incident.confidence, result.confidence)
        incident.affected_areas = [zone.label for zone in result.zones] or result.affected_areas or incident.affected_areas
        incident.updated_at = datetime.now(UTC)
        incident.version += 1
        incident = self.planner.recompute(incident)
        await self.store.upsert(incident)
        self.decision_logger.info(
            "incident_updated_from_sar event_id=%s version=%s",
            incident.event_id,
            incident.version,
        )
        return incident

    async def record_sos_message(self, event_id: str, message: SOSMessage) -> IncidentState:
        incident = await self._get_or_create(event_id)
        incident.sos_messages.append(message)
        incident.sos_reports.append(message)
        incident.updated_at = datetime.now(UTC)
        incident.version += 1
        incident = self.planner.recompute(incident)
        await self.store.upsert(incident)
        self.app_logger.info("sos_message_recorded event_id=%s source=%s", event_id, message.source)
        return incident

    async def record_rag_result(self, result: RagResult) -> IncidentState:
        incident = await self._get_or_create(result.event_id)
        incident.rag_result = result
        incident.rag_summary = result.summary
        incident.rag_context_titles = [item.title for item in result.context_items]
        incident.rag_recommended_actions = result.recommended_actions
        incident.updated_at = datetime.now(UTC)
        incident.version += 1
        incident = self.planner.recompute(incident)
        await self.store.upsert(incident)
        self.decision_logger.info(
            "rag_context_applied event_id=%s version=%s",
            incident.event_id,
            incident.version,
        )
        return incident

    async def enrich_with_rag(self, event_id: str) -> IncidentState:
        incident = await self._get_or_create(event_id)
        rag_query = RagQuery(
            event_id=incident.event_id,
            disaster_type=incident.disaster_type,
            location=incident.location,
            summary=incident.ai_assessment,
            keywords=incident.keywords,
            coordinate=incident.coordinate,
            flood_detected=incident.flood_detected,
            flood_seriousness=incident.flood_seriousness,
            estimated_water_depth_ft=incident.sar.estimated_water_depth_ft,
            affected_areas=incident.affected_areas,
            humans_detected=incident.optical.humans_detected,
        )
        result = await self.rag_provider.enrich(rag_query)
        return await self.record_rag_result(result)

    async def record_field_acknowledgement(
        self, event_id: str, acknowledgement: FieldAcknowledgement
    ) -> IncidentState:
        incident = await self._get_or_create(event_id)
        incident.field_acknowledgements.append(acknowledgement)
        incident.updated_at = datetime.now(UTC)
        incident.version += 1
        incident = self.planner.recompute(incident)
        await self.store.upsert(incident)
        self.field_logger.info(
            "field_acknowledgement event_id=%s team_id=%s status=%s",
            event_id,
            acknowledgement.team_id,
            acknowledgement.status,
        )
        return incident

    async def send_sos_notification(
        self, event_id: str, channel_name: str, recipient: str, message: str
    ) -> IncidentState:
        channel = self.communication_channels[channel_name]
        await channel.send_message(recipient, message)
        return await self.record_sos_message(
            event_id,
            SOSMessage(
                source="manual",
                sender=recipient,
                message=message,
                credibility_score=1.0,
            ),
        )

    async def get_incident(self, event_id: str) -> IncidentState:
        return await self._get_or_create(event_id)

    async def get_dashboard_payload(self, event_id: str) -> DashboardPayload:
        incident = await self._get_or_create(event_id)
        return self.projector.project(incident)

    def _apply_frame_context(self, incident: IncidentState, frame: SensorFrame) -> None:
        location_name = getattr(frame, "location_name", None)
        coordinate = getattr(frame, "coordinate", None)
        if location_name:
            incident.location_name = location_name
            incident.location = location_name
        if coordinate:
            incident.coordinate = coordinate
            incident.rs_coords = f"{coordinate.lat:.5f}, {coordinate.lon:.5f}"
