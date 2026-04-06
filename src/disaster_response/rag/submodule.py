import asyncio

from src.disaster_response.contracts.rag import RagContextItem, RagQuery, RagResult
from src.disaster_response.core.logging_config import get_logger
from src.disaster_response.rag.base import RagProvider


DEFAULT_LAT = 19.0760
DEFAULT_LON = 72.8777


class SubmoduleRagProvider(RagProvider):
    """Adapter from backend RagProvider contract to src/rag submodule pipeline."""

    def __init__(self, pipeline: object | None = None) -> None:
        self._logger = get_logger("disaster_response.models")
        self._pipeline = pipeline
        self._initialization_error: str | None = None
        self._init_lock = asyncio.Lock()

    async def enrich(self, query: RagQuery) -> RagResult:
        await self._ensure_pipeline()
        if self._pipeline is None:
            reason = self._initialization_error or "submodule pipeline unavailable"
            return self._fallback(query, reason)

        try:
            drone_input = self._to_drone_input(query)
            rag_response = await self._process_async(drone_input)
            return self._map_response(query.event_id, rag_response)
        except Exception as exc:
            self._logger.exception("rag_submodule_enrich_failed event_id=%s error=%s", query.event_id, exc)
            return self._fallback(query, str(exc))

    async def _ensure_pipeline(self) -> None:
        if self._pipeline is not None or self._initialization_error:
            return

        async with self._init_lock:
            if self._pipeline is not None or self._initialization_error:
                return

            try:
                from rag.rag.rag_pipeline import DisasterRAGPipeline

                # Pipeline initialization loads embeddings/data/clients; keep off event loop.
                self._pipeline = await asyncio.to_thread(DisasterRAGPipeline)
            except Exception as exc:  # pragma: no cover - depends on optional deps/env
                self._initialization_error = str(exc)
                self._pipeline = None
                self._logger.exception("rag_submodule_init_failed error=%s", exc)

    async def _process_async(self, drone_input: object) -> object:
        assert self._pipeline is not None
        async_method = getattr(self._pipeline, "process_drone_input_async", None)
        if callable(async_method):
            return await async_method(drone_input)

        sync_method = getattr(self._pipeline, "process_drone_input", None)
        if callable(sync_method):
            return await asyncio.to_thread(sync_method, drone_input)

        raise RuntimeError("Pipeline does not expose process_drone_input or process_drone_input_async")

    def _to_drone_input(self, query: RagQuery) -> object:
        from rag.models.drone_input import DroneInput, SeverityLevel

        severity_map = {
            "none": SeverityLevel.LOW,
            "low": SeverityLevel.LOW,
            "moderate": SeverityLevel.MEDIUM,
            "high": SeverityLevel.HIGH,
            "critical": SeverityLevel.CRITICAL,
        }
        severity = severity_map.get(query.flood_seriousness or "low", SeverityLevel.LOW)

        latitude = query.coordinate.lat if query.coordinate else DEFAULT_LAT
        longitude = query.coordinate.lon if query.coordinate else DEFAULT_LON
        flood_depth_cm = (query.estimated_water_depth_ft or 0.0) * 30.48

        # Keep deterministic hint when no area estimate available.
        affected_area_sq_km = float(max(len(query.affected_areas), 1))

        return DroneInput(
            latitude=latitude,
            longitude=longitude,
            flood_depth_cm=flood_depth_cm,
            severity=severity,
            affected_area_sq_km=affected_area_sq_km,
            drone_id=f"EVENT-{query.event_id}",
        )

    def _map_response(self, event_id: str, rag_response: object) -> RagResult:
        recommended_actions = self._collect_recommended_actions(rag_response)
        context_items = self._collect_context_items(rag_response)
        summary = self._compose_summary(rag_response)
        return RagResult(
            event_id=event_id,
            summary=summary,
            recommended_actions=recommended_actions,
            context_items=context_items,
        )

    def _collect_recommended_actions(self, rag_response: object) -> list[str]:
        actions: list[str] = []
        for technique in getattr(rag_response, "recommended_techniques", []) or []:
            actions.append(f"Apply technique: {technique}")
        for resource in getattr(rag_response, "resources_needed", []) or []:
            actions.append(f"Mobilize resource: {resource}")
        if not actions:
            actions.append("Continue sensor-driven monitoring and dispatch readiness checks")
        return list(dict.fromkeys(actions))

    def _collect_context_items(self, rag_response: object) -> list[RagContextItem]:
        items: list[RagContextItem] = []

        for shelter in getattr(rag_response, "relevant_shelters", []) or []:
            distance = getattr(shelter, "distance_km", None)
            if distance is None:
                relevance = 0.7
            else:
                relevance = max(0.1, min(1.0, 1.0 - (float(distance) / 50.0)))
            items.append(
                RagContextItem(
                    source_type="shelter",
                    title=getattr(shelter, "name", "Shelter"),
                    content=(
                        f"location={getattr(shelter, 'location', 'unknown')}; "
                        f"capacity={getattr(shelter, 'capacity', 'n/a')}; "
                        f"occupancy={getattr(shelter, 'current_occupancy', 'n/a')}; "
                        f"distance_km={distance if distance is not None else 'n/a'}"
                    ),
                    relevance_score=relevance,
                )
            )

        for operation in getattr(rag_response, "relevant_operations", []) or []:
            severity_obj = getattr(operation, "severity", None)
            severity = getattr(severity_obj, "value", str(severity_obj or "unknown"))
            items.append(
                RagContextItem(
                    source_type="historical_operation",
                    title=getattr(operation, "operation_id", "Historical Operation"),
                    content=(
                        f"location={getattr(operation, 'location', 'unknown')}; "
                        f"severity={severity}; "
                        f"outcome={getattr(operation, 'outcome', 'n/a')}; "
                        f"lessons={getattr(operation, 'lessons_learned', 'n/a')}"
                    ),
                    relevance_score=0.75,
                )
            )

        return items

    def _compose_summary(self, rag_response: object) -> str:
        rescuer_message = getattr(rag_response, "message_rescuer", "") or ""
        victim_message = getattr(rag_response, "message_victim", "") or ""

        raw_confidence = getattr(rag_response, "confidence_score", None)
        if isinstance(raw_confidence, tuple) and len(raw_confidence) == 2:
            confidence_text = f"{raw_confidence[0]} ({raw_confidence[1]})"
        elif raw_confidence is None:
            confidence_text = "unknown"
        else:
            confidence_text = str(raw_confidence)

        summary_body = rescuer_message.strip() or victim_message.strip() or "No RAG narrative generated."
        summary_body = " ".join(summary_body.split())[:320]
        return f"{summary_body} Confidence: {confidence_text}."

    def _fallback(self, query: RagQuery, reason: str) -> RagResult:
        return RagResult(
            event_id=query.event_id,
            summary=f"RAG enrichment unavailable ({reason}). Continue sensor-led planning with SOP defaults.",
            recommended_actions=[
                "Validate latest SAR and optical outputs",
                "Apply baseline flood SOP until RAG context is restored",
            ],
            context_items=[],
        )
