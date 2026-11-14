"""Render Short #13 with animated Inter-font overlays, lower thirds, and progress bar."""

import sys
import os
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from pathlib import Path
from app.services.render_engine import (
    RenderPipeline,
    build_short_13_render_spec,
)

ROOT_DIR = Path(__file__).resolve().parent.parent

# Resolve media paths with local repository first, then machine fallback
DEMO = ROOT_DIR / "assets" / "sample-media" / "demo-recording-1.mp4"
if not DEMO.exists():
    _dev_demo = Path(r"C:\Users\hirth\TellOS\PG_Automation\Ecommerce\research\tell-os-remotion-project\public\demo-recording-1.mp4")
    if _dev_demo.exists():
        DEMO = _dev_demo

BROLL = ROOT_DIR / "assets" / "sample-media" / "broll-spreadsheet.mp4"
if not BROLL.exists():
    _dev_broll = Path(r"c:\Users\hirth\hirthick-professional\video-editor\broll-spreadsheet.mp4")
    if _dev_broll.exists():
        BROLL = _dev_broll

MUSIC = ROOT_DIR / "assets" / "sample-media" / "bg-music.mp3"
if not MUSIC.exists():
    _dev_music = Path(r"c:\Users\hirth\hirthick-professional\video-editor\bg-music.mp3")
    if _dev_music.exists():
        MUSIC = _dev_music

OUTPUT = ROOT_DIR / "reports" / "short-13-final-render.mp4"

print("=" * 60)
print("HIRTHICK'S VISION STUDIO — Animated Short #13 Render")
print("=" * 60)
print(f"  Demo:   {DEMO} ({'OK' if DEMO.exists() else 'MISSING'})")
print(f"  B-roll: {BROLL} ({'OK' if BROLL.exists() else 'MISSING'})")
print(f"  Music:  {MUSIC} ({'OK' if MUSIC.exists() else 'MISSING'})")
print(f"  Output: {OUTPUT}")
print()

t0 = time.perf_counter()

spec = build_short_13_render_spec(DEMO, BROLL, MUSIC, OUTPUT)
pipeline = RenderPipeline()

print(f"Animation plan: {len(spec.captions)} captions, {len(spec.lower_thirds)} lower-thirds, progress bar")
print(f"Generating 900 animated overlay frames + ffmpeg composition...")
print()

pipeline.render_short(spec)

elapsed = time.perf_counter() - t0
size_mb = OUTPUT.stat().st_size / (1024 * 1024)
print()
print("=" * 60)
print(f"RENDER COMPLETE in {elapsed:.1f}s")
print(f"  Output: {OUTPUT}")
print(f"  Size:   {size_mb:.2f} MB")
print("=" * 60)

