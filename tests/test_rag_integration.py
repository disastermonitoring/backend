import asyncio
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from src.disaster_response.contracts.events import Coordinate  # noqa: E402
from src.disaster_response.contracts.rag import RagQuery  # noqa: E402
from src.disaster_response.rag.submodule import SubmoduleRagProvider  # noqa: E402


def test_submodule_provider_enrich_with_real_pipeline_prints_output() -> None:
    try:
        from rag.rag.rag_pipeline import DisasterRAGPipeline

        pipeline = DisasterRAGPipeline()
    except Exception as exc:
        pytest.skip(f"Real RAG pipeline unavailable in this environment: {exc}")

    provider = SubmoduleRagProvider(pipeline=pipeline)
    query = RagQuery(
        event_id="evt-rag-live-001",
        disaster_type="Flood",
        location="Kottayam, Kerala",
        summary="SAR high flood severity; optical shows humans on rooftops.",
        keywords=["Flood", "Evacuation", "People Seen"],
        coordinate=Coordinate(lat=19.00, lon=72.5386),
        flood_detected=True,
        flood_seriousness="high",
        estimated_water_depth_ft=4.2,
        affected_areas=["Kottayam District"],
        humans_detected=6,
    )
    result = asyncio.run(provider.enrich(query))

    print("\n=== SubmoduleRagProvider.enrich output ===")
    print("event_id:", result.event_id)
    print("summary:", result.summary)
    print("recommended_actions:", result.recommended_actions)
    print("context_items_count:", len(result.context_items))
    for idx, item in enumerate(result.context_items[:3], start=1):
        print(f"context_item_{idx}:", item.source_type, "|", item.title, "|", item.relevance_score)

    assert result.event_id == query.event_id
