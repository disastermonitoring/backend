import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from src.disaster_response.contracts.events import Coordinate, SensorFrame
from src.disaster_response.core.logging_config import get_logger
from src.disaster_response.services.incidents import IncidentService


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


@dataclass(frozen=True)
class CorrelatedFramePair:
    event_id: str
    optical_path: Path
    sar_path: Path


class DirectoryFeederConfig(BaseModel):
    optical_dir: Path
    sar_dir: Path
    location_name: str
    coordinate: Coordinate
    optical_source_id: str = "drone-optical-1"
    sar_source_id: str = "drone-sar-1"
    interval_seconds: float = Field(default=1.0, ge=0.0)


class DirectoryFeederResult(BaseModel):
    processed_pairs: int = Field(default=0, ge=0)
    processed_event_ids: list[str] = Field(default_factory=list)


class DirectoryFrameFeeder:
    def __init__(self, incident_service: IncidentService, sleep_func=None) -> None:
        self._incident_service = incident_service
        self._processed_keys: set[tuple[str, str]] = set()
        self._sleep = sleep_func or asyncio.sleep
        self._logger = get_logger("disaster_response")

    async def run_once(self, config: DirectoryFeederConfig) -> DirectoryFeederResult:
        pairs = self._discover_pairs(config.optical_dir, config.sar_dir)
        processed_event_ids: list[str] = []

        for pair in pairs:
            key = (str(pair.optical_path.resolve()), str(pair.sar_path.resolve()))
            if key in self._processed_keys:
                continue

            captured_at = datetime.now(UTC)
            optical_frame = SensorFrame(
                event_id=pair.event_id,
                sensor_type="optical",
                frame_id=pair.optical_path.stem,
                captured_at=captured_at,
                source_id=config.optical_source_id,
                payload_uri=pair.optical_path.resolve().as_uri(),
                location_name=config.location_name,
                coordinate=config.coordinate,
            )
            sar_frame = SensorFrame(
                event_id=pair.event_id,
                sensor_type="sar",
                frame_id=pair.sar_path.stem,
                captured_at=captured_at,
                source_id=config.sar_source_id,
                payload_uri=pair.sar_path.resolve().as_uri(),
                location_name=config.location_name,
                coordinate=config.coordinate,
            )

            await self._incident_service.ingest_optical_frame(optical_frame)
            await self._incident_service.ingest_sar_frame(sar_frame)

            self._processed_keys.add(key)
            processed_event_ids.append(pair.event_id)
            self._logger.info(
                "directory_feeder_pair_processed event_id=%s optical=%s sar=%s",
                pair.event_id,
                pair.optical_path.name,
                pair.sar_path.name,
            )

            if config.interval_seconds > 0:
                await self._sleep(config.interval_seconds)

        return DirectoryFeederResult(
            processed_pairs=len(processed_event_ids),
            processed_event_ids=processed_event_ids,
        )

    def _discover_pairs(self, optical_dir: Path, sar_dir: Path) -> list[CorrelatedFramePair]:
        optical_files = self._list_image_files(optical_dir)
        sar_files = self._list_image_files(sar_dir)
        sar_by_stem = {path.stem: path for path in sar_files}
        matched_sar_stems: set[str] = set()
        pairs: list[CorrelatedFramePair] = []

        for optical_path in optical_files:
            sar_path = sar_by_stem.get(optical_path.stem)
            if sar_path is None:
                continue
            matched_sar_stems.add(optical_path.stem)
            pairs.append(
                CorrelatedFramePair(
                    event_id=f"evt-{optical_path.stem}",
                    optical_path=optical_path,
                    sar_path=sar_path,
                )
            )

        remaining_optical = [path for path in optical_files if path.stem not in matched_sar_stems]
        remaining_sar = [path for path in sar_files if path.stem not in matched_sar_stems]
        for index, (optical_path, sar_path) in enumerate(zip(remaining_optical, remaining_sar), start=1):
            pairs.append(
                CorrelatedFramePair(
                    event_id=f"evt-pair-{index:04d}",
                    optical_path=optical_path,
                    sar_path=sar_path,
                )
            )

        return pairs

    def _list_image_files(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(
            [
                path
                for path in directory.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            ],
            key=lambda path: path.name,
        )
