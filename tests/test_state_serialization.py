"""Test 1: Strongly typed ProductionState serialization and deserialization."""

import json
from app.state.enums import AssetType, CritiqueAspect, JobStatus, ProductionStage, ReviewStatus
from app.state.models import (
    AssetRecord,
    CritiqueReportRecord,
    EditPlanRecord,
    PublishingPackageRecord,
    ScriptRecord,
    ShotItem,
    ShotPlanRecord,
    TrackPlan,
)
from app.state.production_state import ProductionState


def test_production_state_roundtrip():
    """Verify that a full ProductionState serializes and deserializes without data loss."""
    state = ProductionState(
        job_id="job_001",
        project_id="proj_001",
        short_id="short_13",
        job_status=JobStatus.RUNNING,
        current_stage=ProductionStage.SCRIPTING,
        completed_nodes=["node_a", "node_b"],
        failed_nodes=[],
        pending_approvals=["SCRIPT_APPROVAL"],
        approved_stages=[ProductionStage.INITIALIZATION],
        rejected_stages=[],
        asset_registry={
            "ast_001": AssetRecord(
                asset_id="ast_001",
                path="C:/media/demo.mp4",
                checksum_sha256="abc123sha256",
                asset_type=AssetType.SCREEN_RECORDING,
                review_status=ReviewStatus.APPROVED,
                duration_frames=900,
                duration_seconds=30.0,
                width=1080,
                height=1920,
                fps=30.0,
            )
        },
        research_results={"market": "PG Owners", "pain_point": "Manual rent tracking"},
        script=ScriptRecord(
            version=1,
            hook_text="Managing 50 PG tenants on WhatsApp?",
            problem_text="Messy rent books and lost payments.",
            solution_text="TellOS automates rent receipts directly in WhatsApp chat.",
            cta_text="Check the link in comments.",
            full_narration="Full narration script text...",
            claims=["Saves 10 hours a month", "Instant WhatsApp receipts"],
            word_count=55,
            estimated_duration_seconds=28.5,
        ),
        shot_plan=ShotPlanRecord(
            version=1,
            shots=[
                ShotItem(
                    shot_id="shot_1",
                    start_frame=0,
                    end_frame=150,
                    description="Opening hook showing WhatsApp screen",
                    required_asset_type=AssetType.SCREEN_RECORDING,
                    matched_asset_id="ast_001",
                )
            ],
            total_target_duration_seconds=30.0,
            coverage_percentage=100.0,
        ),
        edit_plan=EditPlanRecord(
            version=1,
            target_width=1080,
            target_height=1920,
            fps=30,
            tracks=[TrackPlan(track_id="V1", track_name="Main", track_type="video", order=0)],
        ),
        critique_report=[
            CritiqueReportRecord(
                aspect=CritiqueAspect.AUDIO_LEVELS,
                score=9.5,
                findings=["Voiceover loud and crisp", "BGM ducked at -18dB"],
                passed=True,
            )
        ],
        publishing_package=PublishingPackageRecord(
            title="Automate PG Rent on WhatsApp in 30 Seconds",
            description="How PG owners track tenant rent effortlessly.",
            tags=["pg", "rent", "automation", "whatsapp"],
        ),
        retry_counts={"node_a": 0},
    )

    # Serialize to JSON dict
    state_dict = state.to_dict()
    assert isinstance(state_dict, dict)
    assert state_dict["job_id"] == "job_001"
    assert state_dict["job_status"] == "RUNNING"
    assert state_dict["current_stage"] == "SCRIPTING"
    assert state_dict["script"]["word_count"] == 55
    assert len(state_dict["asset_registry"]) == 1

    # Roundtrip JSON string
    json_str = json.dumps(state_dict)
    loaded_dict = json.loads(json_str)
    restored = ProductionState.from_dict(loaded_dict)

    assert restored.job_id == state.job_id
    assert restored.project_id == state.project_id
    assert restored.script.hook_text == "Managing 50 PG tenants on WhatsApp?"
    assert restored.shot_plan.shots[0].shot_id == "shot_1"
    assert restored.critique_report[0].aspect == CritiqueAspect.AUDIO_LEVELS
    assert restored.asset_registry["ast_001"].duration_frames == 900


def test_production_state_version_bump():
    """Verify that state version bumps and updated_at updates upon touch()."""
    state = ProductionState(job_id="job_002", project_id="p", short_id="s")
    v1 = state.state_version
    t1 = state.updated_at
    state.touch()
    assert state.state_version == v1 + 1
    assert state.updated_at >= t1

