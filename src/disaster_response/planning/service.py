from datetime import UTC, datetime
from typing import Literal

from disaster_response.contracts.dashboard import ResourcePayload
from disaster_response.contracts.incident import IncidentState, PlanningState
from disaster_response.contracts.rag import RagQuery, RagResult
from disaster_response.core.logging_config import get_logger
from disaster_response.rag.base import RagProvider
from disaster_response.rag.mock import NullRagProvider


class PlanningService:
    def __init__(self, rag_provider: RagProvider | None = None) -> None:
        self._rag_provider = rag_provider or NullRagProvider()
        self._logger = get_logger("disaster_response.decisions")

    async def refresh(self, incident: IncidentState) -> IncidentState:
        summary = self._build_summary(incident)
        rag_result = await self._rag_provider.enrich(
            RagQuery(
                event_id=incident.event_id,
                disaster_type=incident.disaster_type,
                location=incident.location_name,
                summary=summary,
                keywords=incident.keywords,
            )
        )
        incident.rag_result = rag_result
        incident.rag_summary = rag_result.summary
        incident.rag_context_titles = [item.title for item in rag_result.context_items]
        incident.rag_recommended_actions = rag_result.recommended_actions
        return self._apply_planning(incident, rag_result)

    def recompute(self, incident: IncidentState) -> IncidentState:
        rag_result = incident.rag_result or RagResult(
            event_id=incident.event_id,
            summary=incident.rag_summary or "RAG provider not configured.",
            recommended_actions=incident.rag_recommended_actions,
            context_items=[],
        )
        incident.rag_summary = rag_result.summary
        return self._apply_planning(incident, rag_result)

    def _apply_planning(self, incident: IncidentState, rag_result: RagResult) -> IncidentState:
        incident.location = incident.location_name
        incident.confidence = max(
            incident.confidence,
            incident.optical.confidence,
            incident.sar.confidence,
            incident.latest_optical_analysis.confidence if incident.latest_optical_analysis else 0.0,
            incident.latest_sar_analysis.confidence if incident.latest_sar_analysis else 0.0,
        )
        incident.flood_detected = incident.sar.flood_detected or incident.flood_detected
        incident.flood_seriousness = incident.sar.seriousness if incident.sar.last_frame_id else incident.flood_seriousness
        incident.affected_areas = incident.sar.affected_areas or incident.affected_areas
        if incident.latest_sar_analysis and not incident.sar.last_frame_id:
            incident.flood_detected = incident.latest_sar_analysis.flood_detected
            incident.flood_seriousness = incident.latest_sar_analysis.seriousness
            incident.affected_areas = [zone.label for zone in incident.latest_sar_analysis.zones]

        humans_detected = self._human_count(incident)
        has_sos = bool(incident.sos_reports or incident.sos_messages)
        has_field_confirmation = any(
            acknowledgement.status in {"confirmed", "blocked"}
            for acknowledgement in incident.field_acknowledgements
        )

        keywords = {"Flood"} if incident.flood_detected else set()
        if humans_detected > 0:
            keywords.add("People Seen")
        if has_sos:
            keywords.add("SOS")
        if incident.flood_seriousness in {"high", "critical"}:
            keywords.update({"Evacuation", "Overflow"})

        resource_payload = ResourcePayload(boats=0, helicopters=0, medical=0, shelters=0)
        current_actions: list[str] = []
        recommended_actions = list(dict.fromkeys(rag_result.recommended_actions))
        recommended_resources: list[str] = []

        if incident.flood_detected:
            recommended_resources.append("Boat")
            resource_payload.boats = 2 if incident.flood_seriousness in {"low", "moderate"} else 6
            resource_payload.shelters = 2 if incident.flood_seriousness in {"low", "moderate"} else 4
            current_actions.append("Assess flooded routes and coordinate evacuations")

        if incident.flood_seriousness in {"high", "critical"}:
            recommended_resources.append("Helicopter")
            resource_payload.helicopters = 1
            current_actions.append("Restrict unsafe bridges and prioritize aerial reconnaissance")

        if humans_detected > 0:
            if not incident.flood_detected:
                recommended_resources.append("Boat")
            recommended_resources.append("Medical")
            resource_payload.medical = max(1, humans_detected // 2)
            current_actions.append("Dispatch rescue teams to detected human clusters")
            recommended_actions.append("Immediate rescue response near human detections")

        if has_sos:
            current_actions.append("Cross-check SOS reports with latest perception output")

        if has_field_confirmation:
            current_actions.append("Prioritize troop-confirmed hazards in follow-up dispatches")

        bridge_status = incident.sar.bridge_status or incident.bridge_status
        if incident.flood_seriousness == "critical":
            bridge_status = "Bridge Collapsed, Severe"
        elif incident.flood_seriousness == "high":
            bridge_status = "Bridge Unsafe, Access Restricted"
        elif not bridge_status or bridge_status == "Unknown":
            bridge_status = "Bridge Inspection Underway"

        route_alert = (
            f"Blocked routes: {', '.join(incident.sar.blocked_routes)}"
            if incident.sar.blocked_routes
            else f"Bridge status: {bridge_status}"
        )
        alerts = [message.message for message in incident.sos_messages[-3:]]
        alerts.extend(
            acknowledgement.note or acknowledgement.message
            for acknowledgement in incident.field_acknowledgements[-3:]
            if (acknowledgement.note or acknowledgement.message)
        )

        ai_assessment = self._build_summary(incident)
        if rag_result.summary and rag_result.summary != "RAG provider not configured.":
            ai_assessment = rag_result.summary

        impact_zones = [
            {
                "level": zone.severity.title(),
                "area": zone.label,
                "color": self._zone_color(zone.severity),
            }
            for zone in incident.sar.zones
        ]
        if not impact_zones and incident.latest_sar_analysis:
            impact_zones = [
                {
                    "level": zone.severity.title(),
                    "area": zone.label,
                    "color": self._zone_color(zone.severity),
                }
                for zone in incident.latest_sar_analysis.zones
            ]

        water_depth = incident.water_depth
        if incident.sar.estimated_water_depth_ft is not None:
            water_depth = (
                f"{incident.sar.estimated_water_depth_ft} ft ({incident.sar.blocked_routes[0]})"
                if incident.sar.blocked_routes
                else f"{incident.sar.estimated_water_depth_ft} ft"
            )
        elif incident.flood_detected and water_depth == "Unknown":
            water_depth = {
                "low": "1.0 ft",
                "moderate": "2.4 ft",
                "high": "3.8 ft",
                "critical": "5.2 ft",
            }.get(incident.flood_seriousness, "Unknown")

        incident.detections = []
        if incident.flood_detected:
            incident.detections.append("Water Detected")
        if incident.sar.blocked_routes or incident.flood_seriousness in {"high", "critical"}:
            incident.detections.append("Road Submerged")
        if humans_detected > 0:
            incident.detections.append("People Seen")

        incident.keywords = sorted(keywords)
        incident.alerts = alerts
        incident.current_actions = current_actions or ["Continue monitoring incoming sensor streams"]
        incident.recommended_resources = list(dict.fromkeys(recommended_resources))
        incident.resources = resource_payload
        incident.water_depth = water_depth
        incident.bridge_status = bridge_status
        incident.route_alert = route_alert
        incident.road_status = "Submerged" if incident.sar.blocked_routes else "No major road blockage recorded"
        incident.flood_spread = incident.flood_seriousness.title()
        incident.impact_zones = impact_zones
        incident.ai_assessment = ai_assessment
        incident.rs_station = "Kottayam Boat Launch" if incident.flood_detected else "District Control Room"
        if incident.coordinate:
            incident.rs_coords = f"{incident.coordinate.lat:.5f}, {incident.coordinate.lon:.5f}"
        elif incident.sar.zones and incident.sar.zones[0].centroid:
            centroid = incident.sar.zones[0].centroid
            incident.rs_coords = f"{centroid.lat:.5f}, {centroid.lon:.5f}"

        incident.planning = PlanningState(
            threat_priority=self._derive_priority(incident),
            keywords=incident.keywords,
            current_actions=incident.current_actions,
            recommended_actions=list(dict.fromkeys(recommended_actions)),
            recommended_resources=incident.recommended_resources,
            resources=incident.resources,
            route_alert=incident.route_alert,
            ai_assessment=incident.ai_assessment,
            rescue_station=incident.rs_station,
            rescue_coordinates=incident.rs_coords,
            updated_at=datetime.now(UTC),
        )
        incident.updated_at = datetime.now(UTC)
        self._logger.info(
            "planning_refresh event_id=%s priority=%s resources=%s actions=%s",
            incident.event_id,
            incident.planning.threat_priority,
            incident.planning.recommended_resources,
            incident.planning.current_actions,
        )
        return incident

    def _build_summary(self, incident: IncidentState) -> str:
        parts: list[str] = [f"{incident.disaster_type} monitoring update for {incident.location_name}."]
        if incident.flood_detected:
            parts.append(
                f"SAR indicates {incident.flood_seriousness} flood impact with confidence {incident.confidence:.2f}."
            )
        else:
            parts.append("SAR has not confirmed flood presence yet.")
        humans_detected = self._human_count(incident)
        if humans_detected:
            parts.append(f"Optical imagery detected {humans_detected} humans.")
        if incident.sos_messages:
            parts.append(f"{len(incident.sos_messages)} SOS reports are active.")
        if incident.field_acknowledgements:
            parts.append(f"{len(incident.field_acknowledgements)} field acknowledgements received.")
        return " ".join(parts)

    def _derive_priority(self, incident: IncidentState) -> Literal["P1", "P2", "P3"]:
        humans_detected = self._human_count(incident)
        if incident.flood_seriousness == "critical" or (humans_detected > 0 and incident.flood_detected):
            return "P1"
        if incident.flood_seriousness in {"moderate", "high"} or incident.sos_messages:
            return "P2"
        return "P3"

    def _human_count(self, incident: IncidentState) -> int:
        return incident.optical.humans_detected or (
            incident.latest_optical_analysis.humans_detected if incident.latest_optical_analysis else 0
        )

    def _zone_color(self, severity: str) -> str:
        return {
            "critical": "red",
            "high": "red",
            "moderate": "orange",
            "low": "yellow",
        }.get(severity, "yellow")
