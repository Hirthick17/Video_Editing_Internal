"""Tests for the animated render engine, easing curves, and overlay generation."""

import pytest
from pathlib import Path
from PIL import Image

from app.services.render_engine import (
    Easing,
    AnimationType,
    FontConfig,
    CaptionAnimation,
    LowerThirdAnimation,
    ProgressBarAnimation,
    OverlayRenderer,
    INTER_FONT,
    W,
    H,
)


def test_easing_functions():
    """Verify easing functions map boundaries [0, 1] monotonically and cleanly."""
    assert Easing.linear(0.0) == 0.0
    assert Easing.linear(1.0) == 1.0

    assert Easing.ease_out_cubic(0.0) == 0.0
    assert Easing.ease_out_cubic(1.0) == 1.0
    assert 0.0 < Easing.ease_out_cubic(0.5) <= 1.0

    assert Easing.ease_in_out_cubic(0.0) == 0.0
    assert Easing.ease_in_out_cubic(1.0) == 1.0

    # Spring boundary checks
    assert Easing.spring(0.0) == 0.0
    assert abs(Easing.spring(1.0) - 1.0) < 0.1


def test_inter_font_loading():
    """Verify Inter font file exists and loads with custom sizes."""
    assert INTER_FONT.exists()
    cfg = FontConfig(family=INTER_FONT, size=48)
    font = cfg.load()
    assert font is not None


def test_word_reveal_overlay_rendering():
    """Test generating a single transparent overlay frame with word reveal animation."""
    renderer = OverlayRenderer()
    caption = CaptionAnimation(
        text="Managing 50 PG tenants with Excel?",
        start_frame=0,
        end_frame=60,
        animation_type=AnimationType.WORD_REVEAL,
        font_config=FontConfig(family=INTER_FONT, size=48),
        accent_word_indices=[1, 2],
    )

    # Frame 0: starting word
    img_start = renderer.render_word_reveal(5, caption)
    assert isinstance(img_start, Image.Image)
    assert img_start.size == (W, H)
    assert img_start.mode == "RGBA"

    # Frame outside boundary should be empty transparent
    img_outside = renderer.render_word_reveal(100, caption)
    assert img_outside.getextrema()[3] == (0, 0)  # Alpha channel is all 0


def test_lower_third_and_progress_bar_rendering():
    """Test generating lower-third and progress bar overlays."""
    renderer = OverlayRenderer()

    lt = LowerThirdAnimation(
        label="CASE STUDY",
        value="TellOS PG Rent Automation",
        start_frame=0,
        end_frame=30,
    )
    img_lt = renderer.render_lower_third(15, lt)
    assert img_lt.size == (W, H)
    assert img_lt.getextrema()[3][1] > 0  # Non-zero alpha present

    pb = ProgressBarAnimation(
        start_frame=0,
        end_frame=100,
        height=4,
    )
    img_pb = renderer.render_progress_bar(50, pb)
    assert img_pb.size == (W, H)
    assert img_pb.getextrema()[3][1] > 0

