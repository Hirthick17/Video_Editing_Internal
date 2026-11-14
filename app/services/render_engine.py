"""High-engagement animated video render engine using Pillow + ffmpeg.

Generates frame-by-frame animated overlays (word reveals, lower thirds,
progress bars, transitions) composited onto authentic footage.
"""

import math
import os
import shutil
import subprocess
import tempfile
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

W, H = 1080, 1920
FPS = 30
TOTAL_FRAMES = 900
FONT_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"
INTER_FONT = FONT_DIR / "Inter-Variable.ttf"
FFMPEG_BIN = Path(
    r"C:\Users\hirth\AppData\Local\Programs\ChatCut\resources"
    r"\app.asar.unpacked\node_modules\ffmpeg-ffprobe-static\ffmpeg.exe"
)

# Brand palette
COLOR_BG_DARK = (7, 10, 14, 230)        # Obsidian dark overlay
COLOR_ACCENT_GREEN = (37, 211, 102)      # WhatsApp Green #25D366
COLOR_WHITE = (255, 255, 255)
COLOR_LIGHT_GRAY = (200, 210, 220)
COLOR_SHADOW = (0, 0, 0, 180)
COLOR_PILL_BG = (37, 211, 102, 40)       # Translucent green pill


# ============================================================================
# Easing Functions
# ============================================================================

class Easing:
    """Professional animation easing curves."""

    @staticmethod
    def linear(t: float) -> float:
        return t

    @staticmethod
    def ease_out_cubic(t: float) -> float:
        return 1.0 - (1.0 - t) ** 3

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        if t < 0.5:
            return 4.0 * t * t * t
        return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0

    @staticmethod
    def ease_out_back(t: float) -> float:
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2

    @staticmethod
    def ease_out_elastic(t: float) -> float:
        if t == 0 or t == 1:
            return t
        return 2.0 ** (-10.0 * t) * math.sin((t * 10.0 - 0.75) * (2 * math.pi / 3)) + 1.0

    @staticmethod
    def spring(t: float, stiffness: float = 180, damping: float = 14) -> float:
        """Critically damped spring motion."""
        omega = math.sqrt(stiffness)
        zeta = damping / (2.0 * omega)
        if zeta < 1.0:
            wd = omega * math.sqrt(1 - zeta * zeta)
            return 1.0 - math.exp(-zeta * omega * t) * (
                math.cos(wd * t) + (zeta * omega / wd) * math.sin(wd * t)
            )
        return 1.0 - (1.0 + omega * t) * math.exp(-omega * t)


# ============================================================================
# Animation Primitives
# ============================================================================

class AnimationType(str, Enum):
    WORD_REVEAL = "word_reveal"
    FADE_IN = "fade_in"
    SLIDE_UP = "slide_up"
    TYPEWRITER = "typewriter"
    HIGHLIGHT_SWEEP = "highlight_sweep"
    SCALE_IN = "scale_in"
    BOUNCE_IN = "bounce_in"


@dataclass
class FontConfig:
    """Font configuration for text rendering."""
    family: Path = INTER_FONT
    size: int = 48
    weight: str = "bold"  # For variable font axis
    color: Tuple[int, ...] = COLOR_WHITE
    outline_width: int = 0
    outline_color: Tuple[int, ...] = (0, 0, 0, 255)
    shadow_offset: Tuple[int, int] = (0, 0)
    shadow_blur: int = 0
    shadow_color: Tuple[int, ...] = (0, 0, 0, 120)
    line_spacing: float = 1.4

    def load(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self.family), self.size)


@dataclass
class CaptionAnimation:
    """Defines an animated caption overlay on the timeline."""
    text: str
    start_frame: int
    end_frame: int
    animation_type: AnimationType = AnimationType.WORD_REVEAL
    font_config: FontConfig = field(default_factory=FontConfig)
    position_y: float = 0.72  # Fraction of screen height
    center_x: bool = True
    entrance_duration_frames: int = 12  # 0.4s at 30fps
    exit_duration_frames: int = 8       # fade-out
    word_stagger_frames: int = 3        # delay between each word
    highlight_color: Optional[Tuple[int, ...]] = None
    accent_word_indices: List[int] = field(default_factory=list)  # Words to highlight


@dataclass
class LowerThirdAnimation:
    """Animated lower-third bar with label and value."""
    label: str
    value: str
    start_frame: int
    end_frame: int
    bar_color: Tuple[int, ...] = COLOR_ACCENT_GREEN
    position_y: float = 0.88
    entrance_frames: int = 15


@dataclass
class ProgressBarAnimation:
    """Thin animated progress bar at bottom or top of frame."""
    start_frame: int
    end_frame: int
    color: Tuple[int, ...] = COLOR_ACCENT_GREEN
    height: int = 4
    position: str = "bottom"  # "top" or "bottom"


@dataclass
class TransitionSpec:
    """Crossfade or other transition between shots."""
    at_frame: int
    duration_frames: int = 8
    transition_type: str = "crossfade"  # crossfade, dip_to_black


# ============================================================================
# Frame-by-Frame Overlay Renderer
# ============================================================================

class OverlayRenderer:
    """Generates per-frame RGBA overlay images for animated text and UI elements."""

    def __init__(self):
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}

    def _get_font(self, config: FontConfig) -> ImageFont.FreeTypeFont:
        key = f"{config.family}_{config.size}"
        if key not in self._font_cache:
            self._font_cache[key] = config.load()
        return self._font_cache[key]

    def render_word_reveal(
        self,
        frame_idx: int,
        caption: CaptionAnimation,
    ) -> Image.Image:
        """Render a single frame of word-by-word reveal animation."""
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        local_frame = frame_idx - caption.start_frame
        total_duration = caption.end_frame - caption.start_frame

        if local_frame < 0 or local_frame >= total_duration:
            return img

        draw = ImageDraw.Draw(img)
        font = self._get_font(caption.font_config)

        words = caption.text.split()
        if not words:
            return img

        # Calculate word positions (centered layout)
        # First, compute total text width to determine line wrapping
        max_width = int(W * 0.85)
        lines = self._wrap_text_words(words, font, max_width)

        y_base = int(H * caption.position_y)
        line_height = int(caption.font_config.size * caption.font_config.line_spacing)

        # Total height of text block
        total_text_height = len(lines) * line_height
        y_start = y_base - total_text_height // 2

        word_global_idx = 0
        for line_idx, line_words in enumerate(lines):
            # Measure line width for centering
            line_text = " ".join(line_words)
            line_bbox = font.getbbox(line_text)
            line_w = line_bbox[2] - line_bbox[0]
            x_start = (W - line_w) // 2

            # Render each word with staggered animation
            current_x = x_start
            for word in line_words:
                word_delay = word_global_idx * caption.word_stagger_frames
                word_progress = (local_frame - word_delay) / max(caption.entrance_duration_frames, 1)
                word_progress = max(0.0, min(1.0, word_progress))

                # Exit fade
                exit_start = total_duration - caption.exit_duration_frames
                if local_frame >= exit_start:
                    exit_progress = (local_frame - exit_start) / max(caption.exit_duration_frames, 1)
                    exit_alpha = 1.0 - Easing.ease_in_out_cubic(min(1.0, exit_progress))
                else:
                    exit_alpha = 1.0

                if word_progress > 0:
                    eased = Easing.ease_out_cubic(word_progress)

                    # Alpha
                    alpha = eased * exit_alpha

                    # Slide up offset
                    slide_offset = int((1.0 - eased) * 20)

                    word_y = y_start + line_idx * line_height - slide_offset

                    # Color: accent highlighted words get green
                    if word_global_idx in caption.accent_word_indices:
                        base_color = COLOR_ACCENT_GREEN
                    else:
                        base_color = caption.font_config.color[:3]

                    color_with_alpha = base_color + (int(255 * alpha),)

                    # Shadow
                    if caption.font_config.shadow_blur > 0 or caption.font_config.shadow_offset != (0, 0):
                        sx = current_x + caption.font_config.shadow_offset[0]
                        sy = word_y + caption.font_config.shadow_offset[1]
                        shadow_alpha = int(caption.font_config.shadow_color[3] * alpha)
                        draw.text(
                            (sx, sy), word, font=font,
                            fill=caption.font_config.shadow_color[:3] + (shadow_alpha,)
                        )

                    # Outline
                    if caption.font_config.outline_width > 0:
                        ow = caption.font_config.outline_width
                        outline_alpha = int(255 * alpha)
                        oc = caption.font_config.outline_color[:3] + (outline_alpha,)
                        for dx in range(-ow, ow + 1):
                            for dy in range(-ow, ow + 1):
                                if dx != 0 or dy != 0:
                                    draw.text((current_x + dx, word_y + dy), word, font=font, fill=oc)

                    # Main text
                    draw.text((current_x, word_y), word, font=font, fill=color_with_alpha)

                # Advance x position
                word_bbox = font.getbbox(word + " ")
                current_x += word_bbox[2] - word_bbox[0]
                word_global_idx += 1

        return img

    def render_lower_third(
        self,
        frame_idx: int,
        lt: LowerThirdAnimation,
    ) -> Image.Image:
        """Render animated lower-third bar."""
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        local = frame_idx - lt.start_frame
        total = lt.end_frame - lt.start_frame
        if local < 0 or local >= total:
            return img

        draw = ImageDraw.Draw(img)

        # Entrance slide
        entrance_progress = min(1.0, local / max(lt.entrance_frames, 1))
        eased = Easing.ease_out_back(entrance_progress)

        # Exit
        exit_start = total - 10
        if local >= exit_start:
            exit_p = (local - exit_start) / 10.0
            alpha_mult = 1.0 - Easing.ease_in_out_cubic(min(1.0, exit_p))
        else:
            alpha_mult = 1.0

        bar_y = int(H * lt.position_y)
        bar_h = 72
        bar_x_offset = int((1.0 - eased) * (-W))

        # Background pill
        pill_alpha = int(200 * alpha_mult)
        draw.rounded_rectangle(
            [bar_x_offset + 40, bar_y, bar_x_offset + W - 40, bar_y + bar_h],
            radius=12,
            fill=(20, 30, 40, pill_alpha),
        )

        # Accent bar on left
        accent_alpha = int(255 * alpha_mult)
        draw.rounded_rectangle(
            [bar_x_offset + 40, bar_y, bar_x_offset + 48, bar_y + bar_h],
            radius=4,
            fill=lt.bar_color + (accent_alpha,),
        )

        # Label text
        label_font = ImageFont.truetype(str(INTER_FONT), 22)
        value_font = ImageFont.truetype(str(INTER_FONT), 30)

        text_alpha = int(255 * alpha_mult)
        draw.text(
            (bar_x_offset + 68, bar_y + 8), lt.label,
            font=label_font, fill=COLOR_LIGHT_GRAY[:3] + (text_alpha,)
        )
        draw.text(
            (bar_x_offset + 68, bar_y + 34), lt.value,
            font=value_font, fill=COLOR_WHITE[:3] + (text_alpha,)
        )

        return img

    def render_progress_bar(
        self,
        frame_idx: int,
        pb: ProgressBarAnimation,
    ) -> Image.Image:
        """Render thin progress bar showing video playback position."""
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        local = frame_idx - pb.start_frame
        total = pb.end_frame - pb.start_frame
        if local < 0 or local >= total:
            return img

        draw = ImageDraw.Draw(img)
        progress = local / max(total - 1, 1)

        if pb.position == "bottom":
            y = H - pb.height
        else:
            y = 0

        # Background track
        draw.rectangle([0, y, W, y + pb.height], fill=(255, 255, 255, 40))
        # Fill
        fill_w = int(W * progress)
        draw.rectangle([0, y, fill_w, y + pb.height], fill=pb.color + (200,))
        # Glow dot at tip
        if fill_w > 2:
            draw.ellipse(
                [fill_w - 5, y - 3, fill_w + 5, y + pb.height + 3],
                fill=pb.color + (255,),
            )

        return img

    def _wrap_text_words(
        self, words: List[str], font: ImageFont.FreeTypeFont, max_width: int
    ) -> List[List[str]]:
        """Wrap words into lines that fit within max_width."""
        lines: List[List[str]] = []
        current_line: List[str] = []
        current_width = 0

        for word in words:
            word_bbox = font.getbbox(word + " ")
            word_w = word_bbox[2] - word_bbox[0]

            if current_width + word_w > max_width and current_line:
                lines.append(current_line)
                current_line = [word]
                current_width = word_w
            else:
                current_line.append(word)
                current_width += word_w

        if current_line:
            lines.append(current_line)
        return lines


# ============================================================================
# Shot Transition Renderer
# ============================================================================

class TransitionRenderer:
    """Generates ffmpeg filter expressions for shot transitions."""

    @staticmethod
    def build_crossfade_filter(transitions: List[TransitionSpec]) -> str:
        """Build ffmpeg xfade filter chain for smooth shot transitions."""
        # For our use case, we use overlay alpha blending
        # since we're working with a single continuous source
        filters = []
        for tr in transitions:
            t_sec = tr.at_frame / FPS
            dur_sec = tr.duration_frames / FPS
            filters.append(f"fade=t=out:st={t_sec - dur_sec}:d={dur_sec}")
            filters.append(f"fade=t=in:st={t_sec}:d={dur_sec}")
        return ",".join(filters)


# ============================================================================
# Full Render Pipeline
# ============================================================================

@dataclass
class RenderSpec:
    """Complete specification for rendering an animated Short."""
    captions: List[CaptionAnimation] = field(default_factory=list)
    lower_thirds: List[LowerThirdAnimation] = field(default_factory=list)
    progress_bar: Optional[ProgressBarAnimation] = None
    transitions: List[TransitionSpec] = field(default_factory=list)
    # Source video segments
    base_video_path: Optional[Path] = None
    broll_video_path: Optional[Path] = None
    broll_start_frame: int = 0
    broll_end_frame: int = 150
    music_path: Optional[Path] = None
    music_volume: float = 0.125  # -18dB
    output_path: Path = Path("output.mp4")


class RenderPipeline:
    """Orchestrates frame-by-frame overlay generation and ffmpeg final composition."""

    def __init__(self):
        self.overlay_renderer = OverlayRenderer()

    def render_short(self, spec: RenderSpec) -> Path:
        """Execute the full render pipeline."""
        work_dir = Path(tempfile.mkdtemp(prefix="hvs_render_"))
        overlay_dir = work_dir / "overlays"
        overlay_dir.mkdir()

        try:
            # Phase 1: Generate overlay frame sequence
            logger.info("Phase 1: Generating %d animated overlay frames...", TOTAL_FRAMES)
            self._generate_overlay_sequence(spec, overlay_dir)

            # Phase 2: Compose with ffmpeg
            logger.info("Phase 2: Compositing with ffmpeg...")
            self._compose_final(spec, overlay_dir, work_dir)

            return spec.output_path

        finally:
            # Clean up temp frames
            try:
                shutil.rmtree(work_dir)
            except Exception:
                pass

    def _generate_overlay_sequence(
        self, spec: RenderSpec, overlay_dir: Path
    ) -> None:
        """Generate transparent PNG overlay for every frame."""
        for frame_idx in range(TOTAL_FRAMES):
            # Start with transparent canvas
            composite = Image.new("RGBA", (W, H), (0, 0, 0, 0))

            # Render all captions
            for caption in spec.captions:
                if caption.start_frame <= frame_idx < caption.end_frame:
                    layer = self.overlay_renderer.render_word_reveal(frame_idx, caption)
                    composite = Image.alpha_composite(composite, layer)

            # Render lower thirds
            for lt in spec.lower_thirds:
                if lt.start_frame <= frame_idx < lt.end_frame:
                    layer = self.overlay_renderer.render_lower_third(frame_idx, lt)
                    composite = Image.alpha_composite(composite, layer)

            # Render progress bar
            if spec.progress_bar:
                pb = spec.progress_bar
                if pb.start_frame <= frame_idx < pb.end_frame:
                    layer = self.overlay_renderer.render_progress_bar(frame_idx, pb)
                    composite = Image.alpha_composite(composite, layer)

            # Save frame
            composite.save(overlay_dir / f"frame_{frame_idx:04d}.png", "PNG")

            if frame_idx % 90 == 0:
                logger.info("  Overlay frame %d / %d", frame_idx, TOTAL_FRAMES)

    def _compose_final(
        self, spec: RenderSpec, overlay_dir: Path, work_dir: Path
    ) -> None:
        """Use ffmpeg to composite base video + b-roll + overlays + music."""
        output = spec.output_path.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        # Build ffmpeg command
        inputs = []
        filter_parts = []

        # Input 0: Base demo video
        inputs.extend(["-i", str(spec.base_video_path)])

        # Input 1: B-roll
        inputs.extend(["-i", str(spec.broll_video_path)])

        # Input 2: Overlay sequence
        overlay_pattern = str(overlay_dir / "frame_%04d.png")
        inputs.extend([
            "-framerate", str(FPS),
            "-i", overlay_pattern,
        ])

        # Input 3: Background music
        inputs.extend(["-i", str(spec.music_path)])

        broll_dur = (spec.broll_end_frame - spec.broll_start_frame) / FPS

        # Complex filter
        filter_complex = (
            # Scale base video to 1080x1920, 30fps
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,fps={FPS},setpts=PTS-STARTPTS[v1];"

            # Scale b-roll to 1080x1920, fade out at end
            f"[1:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,fps={FPS},setpts=PTS-STARTPTS,"
            f"fade=t=out:st={broll_dur - 0.5}:d=0.5[broll];"

            # Overlay b-roll on base for first N seconds
            f"[v1][broll]overlay=0:0:enable='between(t,0,{broll_dur})'[vbase];"

            # Subtle Ken Burns slow zoom on base (1.0 -> 1.03 over 30s)
            f"[vbase]zoompan=z='1+0.001*in_w/1080*on/{TOTAL_FRAMES}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s=1080x1920:fps={FPS}[vzoom];"

            # Add slight vignette for cinematic feel
            f"[vzoom]vignette=PI/5[vvig];"

            # Overlay animated text frames
            f"[vvig][2:v]overlay=0:0:format=auto[vout];"

            # Audio: demo audio at unity + music ducked
            f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.0[a1];"
            f"[3:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"volume={spec.music_volume}[a2];"
            f"[a1][a2]amix=inputs=2:duration=shortest:dropout_transition=2[aout]"
        )

        cmd = [
            str(FFMPEG_BIN), "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", str(TOTAL_FRAMES / FPS),
            "-movflags", "+faststart",
            str(output),
        ]

        logger.info("Running ffmpeg compose: %s", " ".join(cmd[:10]))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error("ffmpeg stderr: %s", result.stderr[-2000:] if result.stderr else "")
            raise RuntimeError(f"ffmpeg composition failed (exit {result.returncode})")

        logger.info("Render complete: %s (%d bytes)", output, output.stat().st_size)


# ============================================================================
# Short #13 Animation Plan
# ============================================================================

def build_short_13_render_spec(
    demo_path: Path,
    broll_path: Path,
    music_path: Path,
    output_path: Path,
) -> RenderSpec:
    """Build the complete animation spec for Short #13."""

    caption_font = FontConfig(
        family=INTER_FONT,
        size=52,
        color=COLOR_WHITE,
        outline_width=3,
        outline_color=(0, 0, 0, 220),
        shadow_offset=(3, 3),
        shadow_blur=6,
        shadow_color=(0, 0, 0, 140),
        line_spacing=1.45,
    )

    accent_font = FontConfig(
        family=INTER_FONT,
        size=58,
        color=COLOR_WHITE,
        outline_width=3,
        outline_color=(0, 0, 0, 220),
        shadow_offset=(3, 4),
        shadow_blur=8,
        shadow_color=(0, 0, 0, 160),
        line_spacing=1.45,
    )

    cta_font = FontConfig(
        family=INTER_FONT,
        size=56,
        color=COLOR_WHITE,
        outline_width=4,
        outline_color=(0, 0, 0, 240),
        shadow_offset=(4, 4),
        shadow_blur=10,
        shadow_color=(0, 0, 0, 180),
        line_spacing=1.5,
    )

    return RenderSpec(
        captions=[
            # Beat 1: HOOK (0-5s, frames 0-150)
            CaptionAnimation(
                text="Managing 50 PG tenants with Excel?",
                start_frame=8,
                end_frame=145,
                animation_type=AnimationType.WORD_REVEAL,
                font_config=accent_font,
                position_y=0.70,
                entrance_duration_frames=10,
                word_stagger_frames=3,
                accent_word_indices=[1, 2, 3],  # "50 PG tenants"
            ),

            # Beat 2: PROBLEM (5-12s, frames 150-360)
            CaptionAnimation(
                text="Every month — hours wasted matching UPI screenshots manually.",
                start_frame=158,
                end_frame=350,
                animation_type=AnimationType.WORD_REVEAL,
                font_config=caption_font,
                position_y=0.72,
                entrance_duration_frames=10,
                word_stagger_frames=3,
                accent_word_indices=[3, 4],  # "hours wasted"
            ),

            # Beat 3: SOLUTION (12-22s, frames 360-660)
            CaptionAnimation(
                text="TellOS reads the receipt instantly",
                start_frame=368,
                end_frame=510,
                animation_type=AnimationType.WORD_REVEAL,
                font_config=accent_font,
                position_y=0.68,
                entrance_duration_frames=10,
                word_stagger_frames=3,
                accent_word_indices=[0],  # "TellOS"
            ),
            CaptionAnimation(
                text="and syncs your Google Sheet — live.",
                start_frame=515,
                end_frame=650,
                animation_type=AnimationType.WORD_REVEAL,
                font_config=caption_font,
                position_y=0.75,
                entrance_duration_frames=10,
                word_stagger_frames=3,
                accent_word_indices=[3, 4],  # "Google Sheet"
            ),

            # Beat 4: CTA (22-30s, frames 660-900)
            CaptionAnimation(
                text="Zero typing. Zero missed rent.",
                start_frame=668,
                end_frame=810,
                animation_type=AnimationType.WORD_REVEAL,
                font_config=cta_font,
                position_y=0.68,
                entrance_duration_frames=12,
                word_stagger_frames=4,
                accent_word_indices=[0, 3],  # "Zero", "Zero"
            ),
            CaptionAnimation(
                text="Link in bio →",
                start_frame=815,
                end_frame=895,
                animation_type=AnimationType.WORD_REVEAL,
                font_config=FontConfig(
                    family=INTER_FONT,
                    size=44,
                    color=COLOR_ACCENT_GREEN,
                    outline_width=2,
                    outline_color=(0, 0, 0, 200),
                    shadow_offset=(2, 2),
                    shadow_blur=6,
                    shadow_color=(0, 0, 0, 120),
                ),
                position_y=0.78,
                entrance_duration_frames=10,
                word_stagger_frames=5,
            ),
        ],

        lower_thirds=[
            LowerThirdAnimation(
                label="CASE STUDY",
                value="TellOS PG Rent Automation — WhatsApp",
                start_frame=20,
                end_frame=130,
                bar_color=COLOR_ACCENT_GREEN,
                position_y=0.88,
                entrance_frames=12,
            ),
            LowerThirdAnimation(
                label="RESULT",
                value="Zero manual entry • Real-time ledger sync",
                start_frame=530,
                end_frame=640,
                bar_color=COLOR_ACCENT_GREEN,
                position_y=0.88,
                entrance_frames=12,
            ),
        ],

        progress_bar=ProgressBarAnimation(
            start_frame=0,
            end_frame=TOTAL_FRAMES,
            color=COLOR_ACCENT_GREEN,
            height=4,
            position="bottom",
        ),

        transitions=[
            TransitionSpec(at_frame=150, duration_frames=8),
            TransitionSpec(at_frame=360, duration_frames=8),
            TransitionSpec(at_frame=660, duration_frames=8),
        ],

        base_video_path=demo_path,
        broll_video_path=broll_path,
        broll_start_frame=0,
        broll_end_frame=150,
        music_path=music_path,
        music_volume=0.125,
        output_path=output_path,
    )

