"""Timecode and frame conversion utilities enforcing half-open integer intervals."""

from typing import Tuple


def frames_to_seconds(frames: int, fps: int = 30) -> float:
    """Convert integer frames to seconds with given frame rate."""
    if fps <= 0:
        raise ValueError("fps must be positive")
    return frames / float(fps)


def seconds_to_frames(seconds: float, fps: int = 30) -> int:
    """Convert seconds to integer frames using round-half-up convention."""
    if fps <= 0:
        raise ValueError("fps must be positive")
    return int(round(seconds * fps))


def validate_interval(start_frame: int, end_frame: int) -> int:
    """Validate half-open interval [start_frame, end_frame) and return duration in frames."""
    if start_frame < 0:
        raise ValueError(f"start_frame ({start_frame}) cannot be negative")
    if end_frame <= start_frame:
        raise ValueError(
            f"end_frame ({end_frame}) must be strictly greater than start_frame ({start_frame})"
        )
    return end_frame - start_frame


def intervals_overlap(
    interval_a: Tuple[int, int], interval_b: Tuple[int, int]
) -> bool:
    """
    Check if two half-open intervals [start_a, end_a) and [start_b, end_b) overlap.
    Two intervals [a, b) and [c, d) overlap if and only if max(a, c) < min(b, d).
    Adjacent intervals like [0, 100) and [100, 200) do NOT overlap.
    """
    start_a, end_a = interval_a
    start_b, end_b = interval_b
    validate_interval(start_a, end_a)
    validate_interval(start_b, end_b)
    return max(start_a, start_b) < min(end_a, end_b)

