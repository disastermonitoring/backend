from src.disaster_response.contracts.dashboard import DashboardPayload, ImpactZonePayload, ResourcePayload
from src.disaster_response.contracts.incident import IncidentState


class DashboardProjector:
    def project(self, incident: IncidentState) -> DashboardPayload:
        return DashboardPayload(
            disaster_type=incident.disaster_type,
            confidence=f"{round(incident.confidence * 100)}%",
            location=incident.location,
            time=incident.updated_at.strftime("%I:%M %p"),
            flood_detected=incident.flood_detected,
            event_id=incident.event_id,
            water_depth=incident.water_depth,
            affected_areas=", ".join(incident.affected_areas) if incident.affected_areas else incident.location,
            bridge_status=incident.bridge_status,
            keywords=incident.keywords,
            alerts=incident.alerts,
            route_alert=incident.route_alert,
            detections=incident.detections,
            impact_zones=[ImpactZonePayload(**zone) for zone in incident.impact_zones],
            road_status=incident.road_status,
            flood_spread=incident.flood_spread,
            resources=ResourcePayload(**incident.resources.model_dump()),
            rs_station=incident.rs_station,
            rs_coords=incident.rs_coords,
            current_actions=incident.current_actions,
            ai_assessment=incident.ai_assessment,
            recommended_resources=incident.recommended_resources,
        )
