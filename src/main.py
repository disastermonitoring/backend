import os

from fastapi import FastAPI

from src.disaster_response.api.routes import router
from src.disaster_response.communications.mock import LoggingSOSChannel
from src.disaster_response.core.logging_config import configure_logging
from src.disaster_response.perception.mock import MockOpticalModelAdapter, MockSarModelAdapter
from src.disaster_response.planning.service import PlanningService
from src.disaster_response.projection.dashboard import DashboardProjector
from src.disaster_response.rag.base import RagProvider
from src.disaster_response.rag.mock import NullRagProvider
from src.disaster_response.rag.submodule import SubmoduleRagProvider
from src.disaster_response.services.incidents import IncidentService
from src.disaster_response.state.store import InMemoryIncidentStore


configure_logging()

app = FastAPI(title="Disaster Response Backend")


def _build_rag_provider() -> RagProvider:
    provider_name = os.getenv("RAG_PROVIDER", "mock").strip().lower()
    if provider_name == "submodule":
        return SubmoduleRagProvider()
    return NullRagProvider()


incident_service = IncidentService(
    store=InMemoryIncidentStore(),
    rag_provider=(rg := _build_rag_provider()),
    optical_adapter=MockOpticalModelAdapter(),
    sar_adapter=MockSarModelAdapter(),
    planner=PlanningService(rg),
    projector=DashboardProjector(),
    communication_channels={
        "sms": LoggingSOSChannel("sms"),
        "whatsapp": LoggingSOSChannel("whatsapp"),
    },
)

app.state.incident_service = incident_service
app.include_router(router)
