# AGENTS.md

## Purpose

This repository is the backend for a disaster-response decision-support system built around continuous remote-sensing inputs, incremental event-state updates, retrieval-augmented reasoning, operator-facing visualization, SOS communication, and closed-loop field feedback.

The project originated from a B.Tech report in `docs/BTP.pdf` and the current implementation direction is defined primarily by:

- `docs/flow_chart_new.svg`
- `docs/intermediate_repr.jsonc`
- `mock_server/data.json`

This file captures the working assumptions and architecture agreed so future contributors can continue from the same baseline.

## High-Level System

The backend should be treated as a streaming fusion and orchestration layer.

Two continuous sensor streams are assumed:

- Low-light optical image stream
- SAR imagery stream

These inputs do not come from real drones yet. They arrive through abstractions that simulate or wrap drone/sensor sources.

## Perception Inputs and Outputs

### Optical Stream

Optical frames are sent to a YOLO-based human-detection subsystem.

Expected output shape includes structured facts such as:

- Number of humans detected
- Human coordinates or bounding boxes
- Confidence values
- Clusters or density indicators if available
- Source frame reference and timestamps

### SAR Stream

SAR frames are sent to a trained ViT-based flood-analysis subsystem.

Expected output shape includes structured facts such as:

- Flood detected or not
- Severity or seriousness level
- Confidence values
- Affected coordinates, regions, or extent
- Water-depth-like indicators if available
- Infrastructure impact hints if available
- Source frame reference and timestamps

### Important Constraint

Model outputs may not yet be available in final form. The backend must therefore be designed around stable interfaces and adapters, not hardcoded assumptions about current model implementations.

## Canonical Internal State

Incoming model outputs should not be pushed directly to the dashboard.

Instead, each subsystem produces partial updates that are merged into a canonical structured disaster-event state. This state should evolve as new sensor frames, SOS data, and field acknowledgements arrive.

The internal state is conceptually aligned with `docs/intermediate_repr.jsonc`, including:

- Event identity and timestamps
- Event source metadata
- Geospatial context
- Disaster classification
- Perception outputs
- Routing constraints
- SOS and field reports
- Recommended actions
- RAG metadata
- Audit and traceability

This internal representation is the system of record for reasoning and downstream projections.

## RAG Layer

After perception facts are merged into internal state, a RAG layer enriches the event with operational context.

The RAG layer should retrieve and synthesize knowledge such as:

- Standard operating procedures
- Location-specific response guidance
- Historical disasters
- Recorded events and outcomes
- Infrastructure or vulnerability context

The role of RAG is to contextualize raw detections and improve actionability. It should enhance the knowledge available to planning and prioritization, not replace sensor inference.

## Planning and Threat Prioritization

The curated state from perception plus RAG is consumed by planning logic, including:

- Threat prioritization
- Action suggestion
- Resource recommendation
- Routing and logistics reasoning

The PlanningAgent should also use field acknowledgements and feedback to improve later recommendations.

## Dashboard Projection

The operator-facing dashboard does not consume the canonical internal JSON directly.

The backend must project internal state into a flatter SSE payload matching the contract demonstrated in:

- `mock_server/data.json`

This payload is intended for human visualization and includes fields like:

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

The system should support Server-Sent Events so the dashboard can subscribe to live updates.

## SOS Communication

The system includes outbound SOS communication via abstracted messaging channels.

For now, SMS and WhatsApp should be represented through a common abstraction:

- `SOSCommunicationChannel`

This abstraction should allow the rest of the system to publish alerts, summaries, or rescue-relevant communications without coupling the application to a specific provider implementation.

## Field Acknowledgement Endpoint

The system includes an endpoint for troops or rescue teams in the field to acknowledge, confirm, or update the information sent to them.

This feedback should be:

- Logged
- Associated with the relevant event
- Considered by the PlanningAgent
- Used to improve future suggestions and threat prioritization

This is part of the project’s closed-loop design.

## Logging and Auditability

Every subsystem is expected to have strong logging and traceability.

This includes:

- Sensor ingestion logs
- Model input logs
- Model output logs
- RAG retrieval and synthesis logs
- Planning and prioritization decision logs
- Dashboard publication logs
- SOS communication logs
- Field acknowledgement logs

Model outputs should be logged in a form useful for inspection and future retraining.

Decisions should be logged in a way that supports auditability and debugging.

## Recommended Architectural Boundaries

Future implementation should likely separate responsibilities across modules similar to:

- Sensor ingestion
- Perception adapters
- Canonical event-state management
- RAG enrichment
- Planning and prioritization
- Dashboard SSE projection
- SOS communication channels
- Field acknowledgement ingestion
- Logging and audit utilities

Exact package names can change, but these boundaries should remain clear.

## Implementation Guidance

- Design around continuous streams, not single request-response inference calls.
- Prefer explicit typed contracts between subsystems.
- Treat perception systems as pluggable producers of structured facts.
- Keep the canonical event representation separate from the dashboard projection format.
- Keep communication providers abstracted behind interfaces.
- Preserve traceability from dashboard/action outputs back to sensor evidence and reasoning.
- Build for incremental updates as new information arrives over time.

## Current Repo Reality

As of this note, the repository is still early-stage. The docs are more mature than the implementation.

The main design references are:

- `docs/BTP.pdf` for project/report context
- `docs/flow_chart_new.svg` for end-to-end workflow
- `docs/intermediate_repr.jsonc` for canonical structured-event ideas
- `mock_server/data.json` for dashboard-facing payload shape

Contributors should align new code with those references unless the architecture is intentionally revised.
