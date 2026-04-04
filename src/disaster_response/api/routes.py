import asyncio
import json
from pathlib import Path
from typing import Annotated
, Path
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from disaster_response.contracts.dashboard import DashboardPayload
from disaster_response.contracts.events import Coordinate, OpticalAnalysisResult, SarAnalysisResult, SensorFrame
from disaster_response.contracts.incident import FieldAcknowledgement, IncidentState, SOSMessage
from disaster_response.contracts.rag import RagResult
from disaster_response.ingestion.feeder import DirectoryFeederConfig, DirectoryFrameFeeder
from disaster_response.services.incidents import IncidentService


router = APIRouter()


class NotifyRequest(BaseModel):
    channel: str
    recipient: str
    message: str


class DirectoryFeedRequest(BaseModel):
    optical_dir: str
    sar_dir: str
    location_name: str
    coordinate: Coordinate
    optical_source_id: str = "drone-optical-1"
    sar_source_id: str = "drone-sar-1"
    interval_seconds: float = 1.0


def get_incident_service(request: Request) -> IncidentService:
    return request.app.state.incident_service


ServiceDep = Annotated[IncidentService, Depends(get_incident_service)]


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/events")
async def list_events(service: ServiceDep) -> list[dict[str, object]]:
    return [incident.model_dump(mode="json") for incident in await service.store.list_events()]


@router.get("/events/{event_id}")
async def get_event(event_id: str, service: ServiceDep) -> dict[str, object]:
    return (await service.get_incident(event_id)).model_dump(mode="json")


@router.get("/events/{event_id}/dashboard")
async def get_dashboard(event_id: str, service: ServiceDep) -> dict[str, object]:
    return (await service.get_dashboard_payload(event_id)).model_dump(mode="json")


@router.post("/events/{event_id}/frames/optical")
async def ingest_optical_frame(event_id: str, frame: SensorFrame, service: ServiceDep) -> dict[str, object]:
    frame.event_id = event_id
    return (await service.ingest_optical_frame(frame)).model_dump(mode="json")


@router.post("/events/{event_id}/frames/sar")
async def ingest_sar_frame(event_id: str, frame: SensorFrame, service: ServiceDep) -> dict[str, object]:
    frame.event_id = event_id
    return (await service.ingest_sar_frame(frame)).model_dump(mode="json")


@router.post("/events/{event_id}/optical-analysis")
async def post_optical_analysis(
    event_id: str, result: OpticalAnalysisResult, service: ServiceDep
) -> dict[str, object]:
    result.event_id = event_id
    return (await service.record_optical_analysis(result)).model_dump(mode="json")


@router.post("/events/{event_id}/sar-analysis")
async def post_sar_analysis(event_id: str, result: SarAnalysisResult, service: ServiceDep) -> dict[str, object]:
    result.event_id = event_id
    return (await service.record_sar_analysis(result)).model_dump(mode="json")


@router.post("/events/{event_id}/sos")
async def post_sos_message(event_id: str, message: SOSMessage, service: ServiceDep) -> dict[str, object]:
    return (await service.record_sos_message(event_id, message)).model_dump(mode="json")


@router.post("/events/{event_id}/rag")
async def post_rag_result(event_id: str, result: RagResult, service: ServiceDep) -> dict[str, object]:
    result.event_id = event_id
    return (await service.record_rag_result(result)).model_dump(mode="json")


@router.post("/events/{event_id}/rag/enrich")
async def enrich_with_rag(event_id: str, service: ServiceDep) -> dict[str, object]:
    return (await service.enrich_with_rag(event_id)).model_dump(mode="json")


@router.post("/events/{event_id}/field-ack")
async def post_field_ack(
    event_id: str, acknowledgement: FieldAcknowledgement, service: ServiceDep
) -> dict[str, object]:
    return (await service.record_field_acknowledgement(event_id, acknowledgement)).model_dump(mode="json")


@router.post("/events/{event_id}/notify")
async def notify_event(event_id: str, request: NotifyRequest, service: ServiceDep) -> dict[str, object]:
    if request.channel not in service.communication_channels:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {request.channel}")
    return (
        await service.send_sos_notification(
            event_id=event_id,
            channel_name=request.channel,
            recipient=request.recipient,
            message=request.message,
        )
    ).model_dump(mode="json")


@router.post("/feeders/directories")
async def feed_directories(request: DirectoryFeedRequest, service: ServiceDep) -> dict[str, object]:
    feeder = DirectoryFrameFeeder(service)
    result = await feeder.run_once(
        DirectoryFeederConfig(
            optical_dir=Path(request.optical_dir),
            sar_dir=Path(request.sar_dir),
            location_name=request.location_name,
            coordinate=request.coordinate,
            optical_source_id=request.optical_source_id,
            sar_source_id=request.sar_source_id,
            interval_seconds=request.interval_seconds,
        )
    )
    return result.model_dump()


@router.get("/events/{event_id}/stream")
async def stream_event(event_id: str, service: ServiceDep) -> EventSourceResponse:
    queue = await service.store.subscribe(event_id)

    async def event_generator():
        try:
            while True:
                incident = await queue.get()
                payload = service.projector.project(incident)
                yield {
                    "event": "incident_update",
                    "data": json.dumps(payload.model_dump()),
                }
        except asyncio.CancelledError:
            raise
        finally:
            await service.store.unsubscribe(event_id, queue)

    return EventSourceResponse(event_generator())
