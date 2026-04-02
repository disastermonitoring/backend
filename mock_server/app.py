import asyncio
import copy
import json
import os
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse


APP_TITLE = "Mock Disaster SSE Server"
DEFAULT_DATA_FILE = Path(__file__).resolve() / "data.json"
UPDATE_INTERVAL_SECONDS = 2

app = FastAPI(title=APP_TITLE)


def get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_seed_payload() -> dict[str, Any]:
    data_file = Path(os.getenv("DATA_FILE", DEFAULT_DATA_FILE))
    with data_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def randomize_percentage(raw_value: str) -> str:
    digits = "".join(character for character in raw_value if character.isdigit())
    current_value = int(digits) if digits else 50
    delta = random.randint(-4, 4)
    next_value = max(1, min(99, current_value + delta))
    return f"{next_value}%"


def randomize_depth(raw_value: str) -> str:
    try:
        current_depth = float(raw_value.split(" ", maxsplit=1)[0])
    except (ValueError, IndexError):
        current_depth = 2.0
    delta = random.uniform(-0.4, 0.6)
    next_depth = max(0.2, round(current_depth + delta, 1))
    suffix = raw_value[raw_value.find(" "):] if " " in raw_value else " ft"
    return f"{next_depth}{suffix}"


def randomize_event_id(raw_value: str) -> str:
    prefix, separator, suffix = raw_value.rpartition("-")
    if separator and suffix.strip().isdigit():
        next_suffix = f"{random.randint(1, 999999):06d}"
        return f"{prefix}-{next_suffix}"
    return f"{raw_value}-{random.randint(100, 999)}"


def mutate_keywords(values: list[str]) -> list[str]:
    pool = [
        "Overflow",
        "Evacuation",
        "Heavy Rainfall",
        "Landslide Risk",
        "Blocked Route",
        "Rescue Needed",
        "Power Outage",
        "Shelter Open",
    ]
    selection = set(values)
    selection.add(random.choice(pool))
    if len(selection) > 3:
        selection = set(random.sample(list(selection), 3))
    return list(selection)


def mutate_alerts(values: list[str]) -> list[str]:
    pool = [
        "Family trapped on rooftop, water rising",
        "Local road fully cut off by debris",
        "Emergency shelter nearing capacity",
        "Rescue boat delayed by strong current",
        "Medical assistance requested in low-lying zone",
    ]
    selection = values[:] if values else []
    if not selection or random.random() > 0.4:
        selection.append(random.choice(pool))
    if len(selection) > 3:
        selection = selection[-3:]
    return selection


def mutate_resources(values: dict[str, int]) -> dict[str, int]:
    next_values = copy.deepcopy(values)
    for key in next_values:
        next_values[key] = max(0, next_values[key] + random.randint(-1, 2))
    return next_values


def mutate_impact_zones(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    levels = ["Low Risk", "Medium Risk", "High Risk"]
    colors = {"Low Risk": "yellow", "Medium Risk": "orange", "High Risk": "red"}
    next_values = copy.deepcopy(values)
    if not next_values:
        return next_values

    zone = random.choice(next_values)
    zone["level"] = random.choice(levels)
    zone["color"] = colors[zone["level"]]
    return next_values


def mutate_payload(seed_payload: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(seed_payload)

    payload["confidence"] = randomize_percentage(str(payload.get("confidence", "50%")))
    payload["water_depth"] = randomize_depth(str(payload.get("water_depth", "2.0 ft")))
    payload["event_id"] = randomize_event_id(str(payload.get("event_id", "EVT-000001")))
    payload["flood_detected"] = random.choice([True, True, True, False])
    payload["bridge_status"] = random.choice(
        [
            "Bridge Collapsed, Severe",
            "Bridge Unsafe, Access Restricted",
            "Bridge Partially Open",
            "Bridge Inspection Underway",
        ]
    )
    payload["road_status"] = random.choice(
        ["Submerged", "Slow Traffic", "Blocked", "Cleared for Emergency Use"]
    )
    payload["flood_spread"] = random.choice(["Low", "Moderate", "High", "Critical"])
    payload["route_alert"] = random.choice(
        [
            "Bridge over NH-183 collapsed",
            "Diversion active via MC Road",
            "Rescue corridor opened for emergency vehicles",
            "Road access restricted due to strong current",
        ]
    )
    payload["keywords"] = mutate_keywords(payload.get("keywords", []))
    payload["alerts"] = mutate_alerts(payload.get("alerts", []))
    payload["resources"] = mutate_resources(payload.get("resources", {}))
    payload["impact_zones"] = mutate_impact_zones(payload.get("impact_zones", []))
    payload["updated_at"] = datetime.now(UTC).isoformat()
    return payload


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/data")
async def current_data() -> JSONResponse:
    return JSONResponse(content=mutate_payload(load_seed_payload()))


@app.get("/stream")
async def stream() -> EventSourceResponse:
    async def event_generator():
        while True:
            payload = mutate_payload(load_seed_payload())
            yield json.dumps(payload)
            await asyncio.sleep(UPDATE_INTERVAL_SECONDS)

    return EventSourceResponse(event_generator())
