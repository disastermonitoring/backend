from fastapi import FastAPI

from disaster_response.api.routes import router
from disaster_response.communications.mock import LoggingSOSChannel
from disaster_response.core.logging_config import configure_logging
from disaster_response.perception.mock import MockOpticalModelAdapter, MockSarModelAdapter
from disaster_response.planning.service import PlanningService
from disaster_response.projection.dashboard import DashboardProjector
from disaster_response.rag.mock import NullRagProvider
from disaster_response.services.incidents import IncidentService
from disaster_response.state.store import InMemoryIncidentStore


configure_logging()

app = FastAPI(title="Disaster Response Backend")
incident_service = IncidentService(
    store=InMemoryIncidentStore(),
    rag_provider=NullRagProvider(),
    optical_adapter=MockOpticalModelAdapter(),
    sar_adapter=MockSarModelAdapter(),
    planner=PlanningService(),
    projector=DashboardProjector(),
    communication_channels={
        "sms": LoggingSOSChannel("sms"),
        "whatsapp": LoggingSOSChannel("whatsapp"),
    },
)

app.state.incident_service = incident_service
app.include_router(router)
