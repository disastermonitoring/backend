from abc import ABC, abstractmethod
from pathlib import Path

from disaster_response.contracts.events import OpticalAnalysisResult, SarAnalysisResult, SensorFrame


class OpticalModel(ABC):
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None

    @abstractmethod
    async def analyze(self, frame: SensorFrame) -> OpticalAnalysisResult:
        """Analyze an optical frame."""


class SarModel(ABC):
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None

    @abstractmethod
    async def analyze(self, frame: SensorFrame) -> SarAnalysisResult:
        """Analyze a SAR frame."""


OpticalModelAdapter = OpticalModel
SarModelAdapter = SarModel
