"""Tests for Layer 02 — Editing Script Agent.

Verifies:
  - TakeSelector: evaluate_take, run_take_selection, best-take scoring
  - StockClipDownloader: extract_keywords, search_pexels/pixabay, clip limits
  - TypographyMapper: caption event mapping, Poppins font, sentence case
  - EditingScriptAgent: full pipeline execution
"""

from pathlib import Path
import pytest

from app.agents.editing_script_agent import (
    CaptionEventType,
    EditingScriptAgent,
    EditingScriptOutput,
    StockClipDownloader,
    StockClipQuery,
    TakeEvaluation,
    TakeSelectionResult,
    TakeSelector,
    TypographyMapper,
)
from app.philosophy import EditingPhilosophy
from app.state.models import (
    AssetRecord,
    AssetType,
    ScriptRecord,
    ShotItem,
    ShotPlanRecord,
    TranscriptionRecord,
    TranscriptionWord,
)


@pytest.fixture
def philosophy():
    return EditingPhilosophy()


@pytest.fixture
def sample_script():
    return ScriptRecord(
        version=1,
        hook_text="Managing 50 PG tenants and still tracking Excel?",
        problem_text=(
            "Every month you chase rent on WhatsApp. "
            "UPI confusion leads to missed payments. "
            "50 tenants — all manual, all chaotic."
        ),
        solution_text="Tellos automates rent collection. One dashboard, zero chaos.",
        cta_text="Link in bio. Try free.",
        claims=["50 tenants → automated"],
        full_narration=(
            "Managing 50 PG tenants and still tracking Excel? "
            "Every month you chase rent on WhatsApp. "
            "UPI confusion leads to missed payments. "
            "50 tenants — all manual, all chaotic. "
            "Tellos automates rent collection. One dashboard, zero chaos. "
            "Link in bio. Try free."
        ),
        word_count=52,
        estimated_duration_seconds=30.0,
    )


@pytest.fixture
def sample_shot_plan():
    return ShotPlanRecord(
        version=1,
        shots=[
            ShotItem(
                shot_id="SHOT-001",
                start_frame=0,
                end_frame=150,
                description="Hook MCU",
                required_asset_type=AssetType.SCREEN_RECORDING,
            ),
            ShotItem(
                shot_id="SHOT-002",
                start_frame=150,
                end_frame=450,
                description="Problem statement",
                required_asset_type=AssetType.SCREEN_RECORDING,
            ),
        ],
        total_target_duration_seconds=30.0,
    )


def test_take_selector_evaluation():
    selector = TakeSelector()
    asset = AssetRecord(
        asset_id="asset_take_1",
        path="assets/take1.mp4",
        checksum_sha256="fake_sha",
        asset_type=AssetType.SCREEN_RECORDING,
    )
    words = [
        TranscriptionWord(word="Managing", start_seconds=0.0, end_seconds=0.5, confidence=0.95),
        TranscriptionWord(word="50", start_seconds=0.5, end_seconds=0.8, confidence=0.92),
        TranscriptionWord(word="tenants", start_seconds=0.8, end_seconds=1.2, confidence=0.90),
    ]
    transcription = TranscriptionRecord(
        asset_id="asset_take_1",
        text="Managing 50 tenants",
        words=words,
    )

    evaluation = selector.evaluate_take(asset, transcription)
    assert isinstance(evaluation, TakeEvaluation)
    assert evaluation.take_id == "asset_take_1"
    assert evaluation.clarity_score > 8.0
    assert 0.0 <= evaluation.overall_score <= 10.0


def test_take_selector_best_selection():
    selector = TakeSelector()
    eval1 = TakeEvaluation(
        take_id="take_1",
        asset_path="path1.mp4",
        transcription_text="Take 1",
        energy_score=7.0,
        clarity_score=7.0,
        pacing_score=8.0,
        overall_score=7.3,
    )
    eval2 = TakeEvaluation(
        take_id="take_2",
        asset_path="path2.mp4",
        transcription_text="Take 2",
        energy_score=9.5,
        clarity_score=9.5,
        pacing_score=9.5,
        overall_score=9.5,
    )
    best = selector.select_best_take([eval1, eval2])
    assert best.take_id == "take_2"
    assert best.selected is True


def test_stock_clip_downloader_keywords(sample_script):
    downloader = StockClipDownloader()
    keywords = downloader.extract_keywords(sample_script)
    assert isinstance(keywords, list)
    assert len(keywords) > 0
    # keywords should contain meaningful words from script
    assert any("tenant" in k.lower() or "excel" in k.lower() or "rent" in k.lower() or "payment" in k.lower() for k in keywords)


def test_stock_clip_downloader_mock_results(sample_script, philosophy):
    downloader = StockClipDownloader()
    clips = downloader.run(
        script=sample_script,
        philosophy=philosophy,
        output_dir=Path("reports/test_stock"),
    )
    assert len(clips) <= philosophy.max_stock_clips
    for clip in clips:
        assert clip.source in ["pexels", "pixabay"]


def test_typography_mapper_events(sample_script, sample_shot_plan, philosophy):
    mapper = TypographyMapper()
    events = mapper.map_script_to_events(sample_script, sample_shot_plan, philosophy)
    assert len(events) >= 5

    # Apply philosophy constraints
    constrained = mapper.apply_philosophy(events, philosophy)
    for event in constrained:
        assert event.font_family == "Poppins"
        assert event.text_case == "sentence_case"
        assert not event.text.isupper() or len(event.text) <= 3  # Acronyms ok


def test_editing_script_agent_run(sample_script, sample_shot_plan, philosophy, tmp_path):
    agent = EditingScriptAgent()
    assets = {
        "take_01": AssetRecord(
            asset_id="take_01",
            path="assets/take1.mp4",
            checksum_sha256="abc",
            asset_type=AssetType.SCREEN_RECORDING,
        )
    }
    transcriptions = {
        "take_01": TranscriptionRecord(
            asset_id="take_01",
            text="Managing 50 PG tenants and still tracking Excel?",
            words=[
                TranscriptionWord(word="Managing", start_seconds=0.0, end_seconds=0.5, confidence=0.9),
                TranscriptionWord(word="50", start_seconds=0.5, end_seconds=1.0, confidence=0.95),
            ],
        )
    }

    output = agent.run(
        script=sample_script,
        shot_plan=sample_shot_plan,
        assets=assets,
        transcriptions=transcriptions,
        philosophy=philosophy,
        output_dir=tmp_path,
    )

    assert isinstance(output, EditingScriptOutput)
    assert isinstance(output.take_selection, TakeSelectionResult)
    assert output.take_selection.selected_take_id == "take_01"
    assert len(output.stock_clips) <= philosophy.max_stock_clips
    assert output.total_caption_events >= 5
    assert (tmp_path / "reports" / "editing_script_output.json").exists()
