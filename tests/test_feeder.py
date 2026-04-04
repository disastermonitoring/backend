import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from disaster_response.communications.mock import LoggingSOSChannel  # noqa: E402
from disaster_response.contracts.events import Coordinate  # noqa: E402
from disaster_response.ingestion.feeder import DirectoryFeederConfig, DirectoryFrameFeeder  # noqa: E402
from disaster_response.perception.mock import MockOpticalModelAdapter, MockSarModelAdapter  # noqa: E402
from disaster_response.planning.service import PlanningService  # noqa: E402
from disaster_response.projection.dashboard import DashboardProjector  # noqa: E402
from disaster_response.rag.mock import NullRagProvider  # noqa: E402
from disaster_response.services.incidents import IncidentService  # noqa: E402
from disaster_response.state.store import InMemoryIncidentStore  # noqa: E402


async def _noop_sleep(seconds: float) -> None:
    return None


def build_service() -> IncidentService:
    return IncidentService(
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


def test_directory_feeder_pairs_matching_stems_and_applies_same_location(tmp_path: Path) -> None:
    async def scenario() -> None:
        optical_dir = tmp_path / "optical"
        sar_dir = tmp_path / "sar"
        optical_dir.mkdir()
        sar_dir.mkdir()

        (optical_dir / "frame-001.jpg").write_text("optical", encoding="utf-8")
        (sar_dir / "frame-001.tif").write_text("sar", encoding="utf-8")

        service = build_service()
        feeder = DirectoryFrameFeeder(service, sleep_func=_noop_sleep)
        result = await feeder.run_once(
            DirectoryFeederConfig(
                optical_dir=optical_dir,
                sar_dir=sar_dir,
                location_name="Kottayam, Kerala",
                coordinate=Coordinate(lat=9.6053, lon=76.5386),
                interval_seconds=0.0,
            )
        )

        assert result.processed_pairs == 1
        assert result.processed_event_ids == ["evt-frame-001"]

        incident = await service.get_incident("evt-frame-001")
        assert incident.location_name == "Kottayam, Kerala"
        assert incident.coordinate is not None
        assert incident.coordinate.lat == 9.6053
        assert incident.latest_optical_analysis is not None
        assert incident.latest_sar_analysis is not None
        assert incident.latest_optical_analysis.frame_id == "frame-001"
        assert incident.latest_sar_analysis.frame_id == "frame-001"

    asyncio.run(scenario())


def test_directory_feeder_falls_back_to_sorted_pairing_and_sleeps_per_pair(tmp_path: Path) -> None:
    async def scenario() -> None:
        optical_dir = tmp_path / "optical"
        sar_dir = tmp_path / "sar"
        optical_dir.mkdir()
        sar_dir.mkdir()

        (optical_dir / "optical-a.jpg").write_text("optical-a", encoding="utf-8")
        (optical_dir / "optical-b.jpg").write_text("optical-b", encoding="utf-8")
        (sar_dir / "sar-a.tif").write_text("sar-a", encoding="utf-8")
        (sar_dir / "sar-b.tif").write_text("sar-b", encoding="utf-8")

        sleep_calls: list[float] = []

        async def capture_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        service = build_service()
        feeder = DirectoryFrameFeeder(service, sleep_func=capture_sleep)
        result = await feeder.run_once(
            DirectoryFeederConfig(
                optical_dir=optical_dir,
                sar_dir=sar_dir,
                location_name="Kumarakom, Kerala",
                coordinate=Coordinate(lat=9.6179, lon=76.5518),
                interval_seconds=1.0,
            )
        )

        assert result.processed_pairs == 2
        assert result.processed_event_ids == ["evt-pair-0001", "evt-pair-0002"]
        assert sleep_calls == [1.0, 1.0]

    asyncio.run(scenario())
