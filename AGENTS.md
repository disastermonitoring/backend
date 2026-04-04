# AGENTS.md

## Purpose

This repository is the backend for a disaster-response decision-support system built around continuous remote-sensing inputs, incremental event-state updates, retrieval-augmented reasoning, operator-facing visualization, SOS communication, and closed-loop field feedback.

The project originated from a B.Tech report in `docs/BTP.pdf` and the current implementation direction is defined primarily by:

- `docs/flow_chart_new.svg`
- `docs/intermediate_repr.jsonc`
- `mock_server/data.json`

This file captures both the original system intent and the current codebase reality so future contributors can continue from the same baseline without re-discovering the architecture from scratch.

## High-Level System

The backend is a streaming fusion and orchestration layer.

Two continuous sensor streams are assumed:

- Low-light optical image stream
- SAR imagery stream

These inputs do not come from real drones yet. They arrive through abstractions that simulate or wrap drone/sensor sources.

## Perception Inputs and Outputs

### Optical Stream

Optical frames are sent to a YOLO-like human-detection subsystem.

Expected output shape includes structured facts such as:

- Number of humans detected
- Human coordinates or bounding boxes
- Confidence values
- Source frame reference and timestamps

### SAR Stream

SAR frames are sent to a ViT-like flood-analysis subsystem.

Expected output shape includes structured facts such as:

- Flood detected or not
- Severity or seriousness level
- Confidence values
- Affected coordinates, regions, or extent
- Water-depth-like indicators if available
- Infrastructure impact hints if available
- Source frame reference and timestamps

### Important Constraint

Model outputs may not yet be available in final form. The backend is therefore designed around stable interfaces and adapters, not hardcoded assumptions about current model implementations.

## Canonical Internal State

Incoming model outputs are not pushed directly to the dashboard.

Instead, subsystems produce partial updates that are merged into a canonical incident state. That state evolves as new sensor frames, SOS data, RAG context, and field acknowledgements arrive.

The internal representation is conceptually aligned with `docs/intermediate_repr.jsonc`, including:

- Event identity and timestamps
- Geospatial context
- Disaster classification
- Perception outputs
- SOS and field reports
- Recommended actions and resources
- RAG-derived context
- Audit and traceability

In the current codebase, the active canonical state contract is implemented in:

- `src/disaster_response/contracts/incident.py`

## RAG Layer

After perception facts are merged into internal state, a RAG layer enriches the event with operational context.

The RAG layer should retrieve and synthesize knowledge such as:

- Standard operating procedures
- Location-specific response guidance
- Historical disasters
- Recorded events and outcomes
- Infrastructure or vulnerability context

The role of RAG is to contextualize raw detections and improve actionability. It should enhance the knowledge available to planning and prioritization, not replace sensor inference.

In the current codebase, RAG is intentionally abstracted and stubbed by:

- `src/disaster_response/rag/base.py`
- `src/disaster_response/rag/mock.py`

## Planning and Threat Prioritization

The curated state from perception plus RAG is consumed by planning logic, including:

- Threat prioritization
- Action suggestion
- Resource recommendation
- Route alerts and operational narrative

Field acknowledgements should influence later recommendations and prioritization.

In the current codebase, this behavior lives in:

- `src/disaster_response/planning/service.py`

## Dashboard Projection

The operator-facing dashboard does not consume the canonical internal JSON directly.

The backend projects internal state into a flatter payload matching the contract demonstrated in:

- `mock_server/data.json`

This payload includes fields like:

- `disaster_type`
- `confidence`
- `location`
- `time`
- `flood_detected`
- `event_id`
- `water_depth`
- `affected_areas`
- `bridge_status`
- `keywords`
- `alerts`
- `route_alert`
- `detections`
- `impact_zones`
- `road_status`
- `flood_spread`
- `resources`
- `rs_station`
- `rs_coords`
- `current_actions`
- `ai_assessment`
- `recommended_resources`

The current projection code lives in:

- `src/disaster_response/projection/dashboard.py`

The system supports Server-Sent Events so the dashboard can subscribe to live incident updates.

## SOS Communication

The system includes outbound SOS communication via abstracted messaging channels.

For now, SMS and WhatsApp are represented through:

- `SOSCommunicationChannel`

The active implementation uses a simple logging-based channel in:

- `src/disaster_response/communications/base.py`
- `src/disaster_response/communications/mock.py`

## Field Acknowledgement Endpoint

The system includes an endpoint for troops or rescue teams in the field to acknowledge, confirm, or update the information sent to them.

This feedback should be:

- Logged
- Associated with the relevant event
- Considered by planning logic
- Used to improve future suggestions and threat prioritization

This is part of the project’s closed-loop design.

## Logging and Auditability

Every subsystem is expected to have strong logging and traceability.

This includes:

- Sensor ingestion logs
- Model input/output logs
- Planning and decision logs
- SOS communication logs
- Field acknowledgement logs

The active logging configuration is in:

- `src/disaster_response/core/logging_config.py`
- `src/disaster_response/core/settings.py`

Current log files are separated into:

- `logs/app.log`
- `logs/models.log`
- `logs/decisions.log`
- `logs/communications.log`
- `logs/field_feedback.log`

## Current Runtime Path

The current active runtime path is:

- `src/disaster_response/main.py`
- `src/disaster_response/api/routes.py`
- `src/disaster_response/services/incidents.py`
- `src/disaster_response/state/store.py`
- `src/disaster_response/planning/service.py`
- `src/disaster_response/projection/dashboard.py`
- `src/disaster_response/perception/base.py`
- `src/disaster_response/perception/mock.py`
- `src/disaster_response/ingestion/feeder.py`
- `src/disaster_response/contracts/events.py`
- `src/disaster_response/contracts/incident.py`
- `src/disaster_response/contracts/dashboard.py`
- `src/disaster_response/rag/base.py`
- `src/disaster_response/rag/mock.py`

`main.py` wires a single in-memory `IncidentService` into FastAPI app state.

## Current API Surface

The active route layer is in `src/disaster_response/api/routes.py`.

Key endpoints include:

- `GET /health`
- `GET /events`
- `GET /events/{event_id}`
- `GET /events/{event_id}/dashboard`
- `POST /events/{event_id}/frames/optical`
- `POST /events/{event_id}/frames/sar`
- `POST /events/{event_id}/optical-analysis`
- `POST /events/{event_id}/sar-analysis`
- `POST /events/{event_id}/sos`
- `POST /events/{event_id}/rag`
- `POST /events/{event_id}/rag/enrich`
- `POST /events/{event_id}/field-ack`
- `POST /events/{event_id}/notify`
- `POST /feeders/directories`
- `GET /events/{event_id}/stream`

## Directory Feeder Loop

The current codebase includes a feeder loop for simulated paired sensor ingestion:

- `src/disaster_response/ingestion/feeder.py`

Behavior:

- reads optical frames from one directory
- reads SAR frames from another directory
- correlates matching stems first
- falls back to sorted pairing for unmatched files
- treats each optical/SAR pair as coming from the same drone location
- assigns the same `event_id`, `location_name`, and `coordinate` to both frames in a pair
- ingests one correlated pair per interval
- uses a default 1 second gap between processed pairs unless overridden

This is the current implementation of the continuous paired sensor-feed simulation.

## Testing and Verification

The current stable test suite is in:

- `tests/test_incident_api.py`
- `tests/test_feeder.py`
- `tests/test_routes.py`

The current verification commands are:

- `PYTHONPATH=src python3 -m compileall src tests`
- `PYTHONPATH=src .venv/bin/python -m pytest -q`

At the time of this update, the expected passing result is:

- `6 passed`

## Cleanup Status

Earlier in the project there were overlapping implementation lanes. The repo has been simplified to one active runtime lane.

Deleted stale source modules included alternate dependency, service, and store paths that were no longer part of the runtime. If you see stale references inside `__pycache__` listings, ignore them; they are generated artifacts, not active source.

When extending the system, keep using the active lane described above rather than reintroducing parallel implementations.

## Implementation Guidance

- Design around continuous streams, not single request-response inference calls.
- Prefer explicit typed contracts between subsystems.
- Treat perception systems as pluggable producers of structured facts.
- Keep the canonical event representation separate from the dashboard projection format.
- Keep communication providers abstracted behind interfaces.
- Preserve traceability from dashboard/action outputs back to sensor evidence and reasoning.
- Build for incremental updates as new information arrives over time.
- Keep the system simple and in-memory unless the user explicitly asks for heavier infrastructure.

## Current Repo Reality

It now contains a working in-memory backend skeleton with:

- incident state management
- mock perception adapters
- RAG abstraction
- planning heuristics
- SOS communication abstraction
- SSE dashboard projection
- directory-based paired frame feeder simulation
- tests for lifecycle, feeder pairing, and route registration

Contributors should preserve the original project intent from the docs while treating the current runtime path as the authoritative implementation baseline.
