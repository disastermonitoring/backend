import asyncio
from collections import defaultdict
from threading import RLock

from src.disaster_response.contracts.incident import IncidentState


class InMemoryIncidentStore:
    def __init__(self) -> None:
        self._events: dict[str, IncidentState] = {}
        self._subscriptions: dict[str, list[asyncio.Queue[IncidentState]]] = defaultdict(list)
        self._lock = RLock()

    async def get(self, event_id: str) -> IncidentState | None:
        with self._lock:
            return self._events.get(event_id)

    async def list_events(self) -> list[IncidentState]:
        with self._lock:
            return list(self._events.values())

    async def upsert(self, incident: IncidentState) -> IncidentState:
        with self._lock:
            self._events[incident.event_id] = incident
            subscribers = list(self._subscriptions.get(incident.event_id, []))
        for queue in subscribers:
            await queue.put(incident)
        return incident

    async def subscribe(self, event_id: str) -> asyncio.Queue[IncidentState]:
        queue: asyncio.Queue[IncidentState] = asyncio.Queue()
        with self._lock:
            self._subscriptions[event_id].append(queue)
            incident = self._events.get(event_id)
        if incident is not None:
            await queue.put(incident)
        return queue

    async def unsubscribe(self, event_id: str, queue: asyncio.Queue[IncidentState]) -> None:
        with self._lock:
            subscribers = self._subscriptions.get(event_id, [])
            if queue in subscribers:
                subscribers.remove(queue)
