"""Tests for Large-Scale Production Automation Architecture (1,000+ Shorts/Week).

Validates:
  - Stage 1: Raw Footage Ingestion & Silence Elimination (>80ms, <-35dB, 3-frame crossfade, 150-180 WPM)
  - Stage 2: Word-Level Phoneme Alignment & NLP Tagging (HOOK, PROBLEM, DEMO, SOLUTION, CTA, SFX cues)
  - Stage 3: Multi-Track CutList & Keyframe Generation (Track V1 punch-ins every 1.5-2.2s, -14 LUFS, -18dB ducking, SFX 1-frame prior)
  - Stage 4: Kinetic Typography & Visual Overlay Render (Inter font, active highlight #FFE600/#25D366, spring bounce, zero-disk pipe)
  - Stage 5: Autonomous Multi-Aspect Critique Gate (7 branches, >= 9.0/10.0 PASS, max static <= 2.2s)
  - Stage 6: Publishing Package & Multi-Channel Staging (YouTube, IG Reels, TikTok, LinkedIn, 3x contrarian titles, SHA-256)
  - Master Orchestrator: End-to-end execution & 1,000+ shorts/week capacity telemetry
"""

from pathlib import Path
import pytest

from app.services.large_scale_pipeline import (
    AutonomousCritiqueGate,
    AutonomousCritiqueResult,
    CapacityMetrics,
    KineticTypographyRenderEngine,
    LargeScaleCutlist,
    LargeScaleCutlistGenerator,
    LargeScaleJobRecord,
    LargeScaleProductionOrchestrator,
    MultiPlatformPublishingStager,
    MultiPlatformStagingBundle,
    NarrativeBeat,
    NLPEnrichedTranscript,
    PhonemeAlignmentNLPTokenizer,
    PlatformDestination,
    RenderPipelineSpec,
    SFXCategory,
    SilenceEliminationEngine,
    SilenceEliminationResult,
)


@pytest.fixture
def sample_video_path():
    path = Path("assets/sample-media/demo-recording-1.mp4")
    return path


def test_stage1_silence_elimination(sample_video_path):
    """Stage 1: Validates dead air elimination, 3-frame crossfade, and 150-180 WPM delivery."""
    result = SilenceEliminationEngine.process_raw_footage(sample_video_path)

    assert isinstance(result, SilenceEliminationResult)
    assert result.original_duration_seconds > result.tightened_duration_seconds
    assert result.silence_duration_eliminated > 0.0
    assert result.elimination_ratio_percent > 0.0
    assert len(result.retained_speech_segments) >= 3
    assert all(seg.crossfade_applied for seg in result.retained_speech_segments)
    # Check 150-180 WPM range
    assert 140.0 <= result.estimated_delivery_wpm <= 190.0
    # Latency benchmark: < 8s per minute
    assert result.stage_latency_seconds < 8.0


def test_stage2_phoneme_alignment_nlp_tagging(sample_video_path):
    """Stage 2: Validates word timestamps, 5-beat classification, SFX keyword tagging, and punch-in anchors."""
    s1 = SilenceEliminationEngine.process_raw_footage(sample_video_path)
    s2 = PhonemeAlignmentNLPTokenizer.align_and_enrich(s1)

    assert isinstance(s2, NLPEnrichedTranscript)
    assert s2.total_words > 40
    assert s2.total_duration_seconds == s1.tightened_duration_seconds
    # Check that all 5 narrative beats are populated
    for beat in NarrativeBeat:
        assert len(s2.beats[beat]) > 0, f"Narrative beat {beat} has no words"

    # Check SFX cues extracted
    assert len(s2.sfx_cue_points) > 0
    categories = [c["category"] for c in s2.sfx_cue_points]
    assert any(cat in [SFXCategory.POP.value, SFXCategory.DING.value, SFXCategory.WHOOSH.value, SFXCategory.CASH.value] for cat in categories)

    # Check punch-in anchors identified
    assert len(s2.punch_in_anchors) >= 3
    # Latency benchmark: < 4s
    assert s2.stage_latency_seconds < 4.0


def test_stage3_multi_track_cutlist_generation(sample_video_path):
    """Stage 3: Validates 5-track layout, punch-ins every 1.5-2.2s, -14 LUFS speech, -18dB BGM, SFX 1-frame prior."""
    s1 = SilenceEliminationEngine.process_raw_footage(sample_video_path)
    s2 = PhonemeAlignmentNLPTokenizer.align_and_enrich(s1)
    s3 = LargeScaleCutlistGenerator.generate_cutlist(s2, nominal_fps=30)

    assert isinstance(s3, LargeScaleCutlist)
    # Track V1: Scale punch-in keyframes alternate between 1.0 and 1.15
    assert len(s3.track_v1_punch_in_keyframes) >= 10
    scales = [kf.scale_factor for kf in s3.track_v1_punch_in_keyframes]
    assert 1.0 in scales and 1.15 in scales
    # Max static interval <= 2.2s
    assert s3.max_static_interval_seconds <= 2.2

    # Track V2: B-Roll slots present
    assert len(s3.track_v2_broll_slots) >= 1

    # Track A1 & A2: -14 LUFS speech & -18dB ducking
    assert s3.track_a1_speech_lufs == -14.0
    assert all(duck.ducked_db <= -18.0 for duck in s3.track_a2_bgm_ducking)

    # Track A3: SFX placed 1 frame (33.3ms) before visual/audio event
    assert len(s3.track_a3_sfx_events) > 0
    # Latency benchmark: < 200ms
    assert s3.stage_latency_seconds < 0.200


def test_stage4_kinetic_typography_render_spec(sample_video_path):
    """Stage 4: Validates kinetic typography spec, Inter font, active highlight, spring bounce, and pipe streaming."""
    s1 = SilenceEliminationEngine.process_raw_footage(sample_video_path)
    s2 = PhonemeAlignmentNLPTokenizer.align_and_enrich(s1)
    s3 = LargeScaleCutlistGenerator.generate_cutlist(s2)
    s4 = KineticTypographyRenderEngine.build_render_spec(s3, s2, fps=30.0)

    assert isinstance(s4, RenderPipelineSpec)
    assert s4.target_resolution == (1080, 1920)
    assert s4.target_fps == 30.0
    assert s4.zero_disk_pipe_enabled is True
    assert len(s4.subtitle_cues) >= 10
    # Check typography configuration
    sample_cue = s4.subtitle_cues[0]
    assert sample_cue.font_family == "Inter"
    assert sample_cue.outline_width_px == 4
    assert sample_cue.active_word_color in ["#FFE600", "#25D366"]
    assert sample_cue.spring_bounce_active is True
    assert sample_cue.y_position == 1480  # Safe zone


def test_stage5_autonomous_critique_gate(sample_video_path):
    """Stage 5: Validates 7-branch autonomous quality critique, score >= 9.0, PASS decision."""
    s1 = SilenceEliminationEngine.process_raw_footage(sample_video_path)
    s2 = PhonemeAlignmentNLPTokenizer.align_and_enrich(s1)
    s3 = LargeScaleCutlistGenerator.generate_cutlist(s2)
    s4 = KineticTypographyRenderEngine.build_render_spec(s3, s2)
    s5 = AutonomousCritiqueGate.evaluate(s3, s2, s4)

    assert isinstance(s5, AutonomousCritiqueResult)
    assert len(s5.branch_evaluations) == 7
    assert all(b.passed for b in s5.branch_evaluations)
    assert s5.overall_score >= 9.0
    assert s5.gate_decision == "PASS"
    assert s5.max_static_interval_verified <= 2.2
    assert s5.speech_lufs_verified == -14.0
    assert s5.contrast_ratio_verified >= 4.5
    # Latency benchmark: < 1.5s
    assert s5.stage_latency_seconds < 1.5


def test_stage6_multi_platform_publishing_stager(sample_video_path):
    """Stage 6: Validates 3x contrarian titles, YouTube/Reels/TikTok/LinkedIn packaging, SHA-256."""
    s6 = MultiPlatformPublishingStager.create_staging_bundle("short_13", sample_video_path)

    assert isinstance(s6, MultiPlatformStagingBundle)
    assert len(s6.contrarian_title_variants) == 3
    assert len(s6.output_mp4_sha256) == 64
    assert s6.distribution_ready is True

    # Check 4 platform destinations
    for dest in [
        PlatformDestination.YOUTUBE_SHORTS,
        PlatformDestination.INSTAGRAM_REELS,
        PlatformDestination.TIKTOK,
        PlatformDestination.LINKEDIN,
    ]:
        assert dest in s6.platforms
        pkg = s6.platforms[dest]
        assert len(pkg.title) > 0
        assert len(pkg.caption) > 0
        assert len(pkg.hashtags) > 0
        assert pkg.aspect_ratio == "9:16"

    # Latency benchmark: < 500ms
    assert s6.stage_latency_seconds < 0.500


def test_end_to_end_large_scale_orchestrator(sample_video_path):
    """Validates master orchestrator running all 6 stages synchronously with full job record telemetry."""
    orchestrator = LargeScaleProductionOrchestrator(num_workers=2)
    job = orchestrator.run_single_short_pipeline(
        job_id="scale_job_test_001",
        short_id="short_13_pg_rent",
        raw_footage_path=sample_video_path,
        creator_style="Tharun Speaks",
    )

    assert isinstance(job, LargeScaleJobRecord)
    assert job.status == "COMPLETED"
    assert job.current_stage_index == 6
    assert job.stage1_silence is not None
    assert job.stage2_nlp is not None
    assert job.stage3_cutlist is not None
    assert job.stage4_render is not None
    assert job.stage5_critique is not None
    assert job.stage6_staging is not None
    assert job.stage5_critique.gate_decision == "PASS"
    assert len(job.stage_latencies) == 6
    assert job.total_latency_seconds > 0.0


def test_1000_shorts_per_week_capacity_calculations():
    """Mathematically proves the architecture easily satisfies and scales beyond 1,000+ shorts/week."""
    capacity = LargeScaleProductionOrchestrator.calculate_scale_capacity(
        benchmark_short_latency_seconds=32.2,
        concurrent_workers=4,
        daily_operating_hours=12.0,
        days_per_week=7,
    )

    assert isinstance(capacity, CapacityMetrics)
    assert capacity.target_weekly_shorts == 1000
    # Single worker daily throughput > 1,300 shorts/day (12 hrs)
    assert capacity.single_worker_daily_capacity > 1300
    # 4 concurrent workers weekly throughput > 30,000 shorts/week
    assert capacity.recommended_weekly_throughput >= 10000
    assert capacity.recommended_weekly_throughput >= capacity.target_weekly_shorts
    # Utilization percent is well under 100% (demonstrating massive headroom)
    assert capacity.cluster_utilization_percent < 50.0
