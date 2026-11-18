#!/usr/bin/env python3
"""
Applies Tharun Speaks phrase-chunked animated captions to the live ChatCut Desktop project.
"""

import sys
import json
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.integrations.chatcut.mcp_adapter import ChatCutMCPAdapter
from app.services.script_service import ScriptService
from app.services.media_understanding_service import MediaUnderstandingService


def main():
    print("Connecting to live ChatCut Desktop...")
    adapter = ChatCutMCPAdapter(mode="live")
    p_id, t_id = adapter.discover_active_project()
    print(f"Active Project: {p_id}, Timeline: {t_id}")

    # 1. Read existing captions & delete old cards
    read_res = adapter._execute_cli_tool("read_captions", {"projectId": p_id, "timelineId": t_id})
    rev = read_res.get("revision")
    existing_cards = read_res.get("cards", [])
    existing_card_ids = [c["id"] for c in existing_cards if "id" in c]

    if existing_card_ids:
        print(f"Deleting {len(existing_card_ids)} existing caption cards...")
        del_res = adapter._execute_cli_tool("edit_captions", {
            "projectId": p_id,
            "timelineId": t_id,
            "action": "delete_cards",
            "revision": rev,
            "json": json.dumps({"cardIds": existing_card_ids})
        })
        rev = del_res.get("revision", rev)

    # 2. Build 19-phrase Tharun Speaks SRT
    script = ScriptService.create_short_13_script()
    transcript = MediaUnderstandingService.generate_word_timed_transcript(script)

    def format_srt_time(seconds: float) -> str:
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    phrase_word_counts = [4, 4, 2, 4, 2, 3, 3, 2, 2, 3, 4, 5, 4, 4, 1, 3, 3, 3, 3]
    words = transcript.words
    cards = []
    idx = 0
    for count in phrase_word_counts:
        chunk = words[idx:idx + count]
        idx += count
        text = " ".join(w.word for w in chunk)
        start_t = chunk[0].start_seconds
        end_t = chunk[-1].end_seconds
        cards.append((start_t, end_t, text))

    srt_lines = []
    for i, (st, et, txt) in enumerate(cards, 1):
        srt_lines.append(f"{i}")
        srt_lines.append(f"{format_srt_time(st)} --> {format_srt_time(et)}")
        srt_lines.append(txt)
        srt_lines.append("")

    full_srt = "\n".join(srt_lines)

    # 3. Import SRT into ChatCut
    print(f"Importing {len(cards)} Tharun Speaks phrase cards into ChatCut Desktop...")
    import_res = adapter._execute_cli_tool("edit_captions", {
        "projectId": p_id,
        "timelineId": t_id,
        "action": "import_subtitles",
        "subtitleContent": full_srt,
        "revision": rev
    })
    rev = import_res.get("revision", rev)
    track_ids = import_res.get("trackIds", [])
    track_id = track_ids[0] if track_ids else None
    print(f"Successfully imported {import_res.get('cardCount', len(cards))} cards on caption track {track_id}!")

    # 4. Apply Tharun Speaks Typography & Accent Style
    tharun_style = {
        "fontFamily": "Inter",
        "fontSize": 0.065,
        "fontStyle": {"weight": "800"},
        "color": "#FFFFFF",
        "strokeColor": "#000000",
        "strokeWidth": 4,
        "textShadow": "0px 4px 12px rgba(0, 0, 0, 0.9)",
        "align": "center",
        "textTransform": "none",
        "activeToken": {
            "color": "#BF40BF",
            "background": None
        }
    }

    if track_id:
        print("Applying Tharun Speaks typography (Inter 800 Bold, White with Black Stroke & #BF40BF Purple Accent)...")
        style_res = adapter._execute_cli_tool("edit_captions", {
            "projectId": p_id,
            "timelineId": t_id,
            "action": "set_track_style",
            "revision": rev,
            "json": json.dumps({
                "trackId": track_id,
                "style": tharun_style,
                "mode": "merge"
            })
        })
        print("Tharun Speaks caption styling active on timeline!")

    # 5. Focus ChatCut Desktop window
    try:
        adapter._execute_cli_tool("target_project", {"projectId": p_id, "openWindow": True})
        print("Brought ChatCut Desktop window to focus.")
    except Exception as e:
        print(f"Window focus notice: {e}")

    print("\nTharun Speaks captions assembly complete!")


if __name__ == "__main__":
    main()
