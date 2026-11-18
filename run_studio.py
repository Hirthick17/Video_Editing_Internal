#!/usr/bin/env python3
"""
Hirthick's Vision Studio - Command Line Video Editor Runner.
Executes the Pattern A automated video editing pipeline directly into ChatCut Desktop via MCP,
without requiring the Web UI.
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.integrations.chatcut.mcp_adapter import ChatCutMCPAdapter
from app.services.assembly_service import AssemblyService
from app.services.audio_library import AudioLibraryService
from app.services.edit_planner_service import EditPlannerService
from app.services.media_understanding_service import MediaUnderstandingService
from app.services.project_scanner import ProjectScannerService
from app.services.script_service import ScriptService
from app.services.shot_planner_service import ShotPlannerService
from app.services.stock_sourcing import StockSourcingService


def print_banner():
    print("=" * 70)
    print("  HIRTHICK'S VISION STUDIO — PATTERN A VIDEO PIPELINE (CLI)")
    print("  Direct ChatCut MCP Desktop Automation (No Web UI)")
    print("=" * 70)


def check_chatcut_live(adapter: ChatCutMCPAdapter):
    """Verify ChatCut Desktop is running and responsive."""
    print("\n[1/5] Checking ChatCut Desktop connection...")
    try:
        proj_id, tl_id = adapter.discover_active_project()
        print(f"  ✓ Connected to ChatCut Desktop!")
        print(f"  ✓ Active Project ID : {proj_id}")
        print(f"  ✓ Active Timeline ID: {tl_id}")
        return proj_id, tl_id
    except Exception as e:
        print(f"  ✗ Could not connect to ChatCut Desktop: {e}")
        print("  Please make sure ChatCut Desktop is running with an open project.")
        sys.exit(1)


def ingest_assets_to_project(adapter: ChatCutMCPAdapter, project_id: str, sample_dir: Path):
    """Ensure media files are ingested into ChatCut Media Pool."""
    print("\n[2/5] Ingesting authentic media assets into ChatCut...")
    media_files = [
        sample_dir / "demo-recording-1.mp4",
        sample_dir / "broll-spreadsheet.mp4",
        sample_dir / "bg-music.mp3",
    ]
    ingested = []
    for f in media_files:
        if f.is_file():
            try:
                res = adapter.push_asset(project_id, str(f.resolve()))
                ingested.append(f.name)
                print(f"  ✓ Ingested: {f.name}")
            except Exception as e:
                print(f"  ! Notice for {f.name}: {e}")
    return ingested


def plan_pattern_a_edits(sample_dir: Path):
    """Generate 4-beat narrative script, shot plan, and atomic 5-track operations."""
    print("\n[3/5] Planning Pattern A editorial timeline...")

    # 1. Project scan
    project = ProjectScannerService.scan_short_13_project(base_dir=sample_dir)
    print(f"  ✓ Verified {len(project.asset_registry)} authentic assets.")

    # 2. Script & Shots
    script = ScriptService.create_short_13_script()
    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)
    print(f"  ✓ Formulated 4-beat script: {script.word_count} words (~{round((script.word_count/script.estimated_duration_seconds)*60, 1)} WPM).")

    # 3. Media Understanding
    transcript = MediaUnderstandingService.generate_word_timed_transcript(script)
    demo_file = sample_dir / "demo-recording-1.mp4"
    broll_file = sample_dir / "broll-spreadsheet.mp4"
    segments = []
    if demo_file.exists():
        segments.extend(MediaUnderstandingService.detect_usable_segments(demo_file, "ast_demo_recording_01"))
    if broll_file.exists():
        segments.extend(MediaUnderstandingService.detect_usable_segments(broll_file, "ast_broll_spreadsheet_01"))
    match_report = MediaUnderstandingService.match_clips_to_shots(shot_plan, segments, project.asset_registry)
    print(f"  ✓ Matched {len(match_report.matches)} footage segments to timeline.")

    # 4. Multi-track edit plan
    edit_plan, operations = EditPlannerService.create_short_13_edit_plan(project, shot_plan, transcript, match_report)
    print(f"  ✓ Planned 5-track layout (V1/V2/A1/A2/TXT) with {len(operations)} atomic operations.")

    return edit_plan, operations


def apply_to_chatcut(adapter: ChatCutMCPAdapter, project_id: str, timeline_id: str, edit_plan, operations):
    """Apply operations to ChatCut Desktop via MCP."""
    print("\n[4/5] Assembling timeline in ChatCut Desktop via MCP...")
    assembly_svc = AssemblyService(adapter=adapter)
    result = assembly_svc.assemble_short_13(
        project_id=project_id,
        timeline_id=timeline_id,
        edit_plan=edit_plan,
        operations=operations,
        operator_id="antigravity_cli",
    )
    print(f"  ✓ Applied {result.applied_operations_count} timeline operations.")
    if result.rollback_snapshot_id:
        print(f"  ✓ Rollback snapshot created: {result.rollback_snapshot_id}")
    return result


def focus_chatcut_window(adapter: ChatCutMCPAdapter, project_id: str):
    """Bring ChatCut Desktop to the front."""
    print("\n[5/5] Focusing ChatCut Desktop window...")
    try:
        adapter._execute_cli_tool("target_project", {"projectId": project_id, "openWindow": True})
        print("  ✓ ChatCut Desktop window focused! Ready for hands-on polish.")
    except Exception as e:
        print(f"  ! Could not focus window automatically: {e}")


def main():
    parser = argparse.ArgumentParser(description="Hirthick's Vision Studio - Direct ChatCut MCP Video Editor")
    parser.add_argument("--mode", choices=["live", "simulated", "auto"], default="live", help="MCP transport mode (default: live)")
    parser.add_argument("--sample-dir", type=str, default="assets/sample-media", help="Path to sample media directory")
    args = parser.parse_args()

    print_banner()
    sample_dir = (PROJECT_ROOT / args.sample_dir).resolve()
    if not sample_dir.exists():
        print(f"Error: Sample directory not found at {sample_dir}")
        sys.exit(1)

    t0 = time.time()
    adapter = ChatCutMCPAdapter(mode=args.mode)

    # Step 1: Connect and discover
    proj_id, tl_id = check_chatcut_live(adapter)

    # Step 2: Ingest authentic media
    ingest_assets_to_project(adapter, proj_id, sample_dir)

    # Step 3: Plan edits
    edit_plan, operations = plan_pattern_a_edits(sample_dir)

    # Step 4: Apply to ChatCut timeline
    apply_to_chatcut(adapter, proj_id, tl_id, edit_plan, operations)

    # Step 5: Focus window
    focus_chatcut_window(adapter, proj_id)

    elapsed = round(time.time() - t0, 2)
    print("\n" + "=" * 70)
    print(f"  PIPELINE COMPLETE in {elapsed}s!")
    print(f"  Switch to your ChatCut Desktop app to review and polish the timeline.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
