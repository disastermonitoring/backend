from disaster_response.contracts.events import OpticalAnalysisResult, SarAnalysisResult, SensorFrame
from disaster_response.core.logging_config import get_logger
from disaster_response.perception.base import OpticalModel, SarModel


class PerceptionService:
    def __init__(self, optical_model: OpticalModel, sar_model: SarModel) -> None:
        self._optical_model = optical_model
        self._sar_model = sar_model
        self._logger = get_logger("disaster_response.models")

    async def analyze_optical(self, frame: SensorFrame) -> OpticalAnalysisResult:
        result = await self._optical_model.analyze(frame)
        self._logger.info(
            "optical_analysis event_id=%s frame_id=%s payload_uri=%s humans=%s confidence=%.2f",
            frame.event_id,
            frame.frame_id,
            frame.payload_uri,
            result.humans_detected,
            result.confidence,
        )
        return result

    async def analyze_sar(self, frame: SensorFrame) -> SarAnalysisResult:
        result = await self._sar_model.analyze(frame)
        self._logger.info(
            "sar_analysis event_id=%s frame_id=%s payload_uri=%s flood_detected=%s seriousness=%s confidence=%.2f",
            frame.event_id,
            frame.frame_id,
            frame.payload_uri,
            result.flood_detected,
            result.seriousness,
            result.confidence,
        )
        return result
