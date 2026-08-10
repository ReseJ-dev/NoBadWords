"""Convert reviewed detections into bounded censorship intervals."""

from collections.abc import Sequence

from app.core.models import CensorInterval, ProfanityMatch

DEFAULT_PRE_PADDING_MS = 120
DEFAULT_POST_PADDING_MS = 180
DEFAULT_MERGE_GAP_MS = 0


def build_censor_intervals(
    detections: Sequence[ProfanityMatch],
    media_duration: float,
    *,
    pre_padding_ms: int = DEFAULT_PRE_PADDING_MS,
    post_padding_ms: int = DEFAULT_POST_PADDING_MS,
    merge_gap_ms: int = DEFAULT_MERGE_GAP_MS,
) -> list[CensorInterval]:
    """Pad, clamp, sort, and merge enabled profanity detections."""
    if media_duration < 0:
        raise ValueError("Media duration cannot be negative.")
    if min(pre_padding_ms, post_padding_ms, merge_gap_ms) < 0:
        raise ValueError("Padding and merge gap values cannot be negative.")

    pre_padding = pre_padding_ms / 1000
    post_padding = post_padding_ms / 1000
    candidates: list[CensorInterval] = []
    for detection in detections:
        if not detection.enabled or detection.end <= detection.start:
            continue
        start = max(0.0, detection.start - pre_padding)
        end = min(media_duration, detection.end + post_padding)
        if end <= start:
            continue
        candidates.append(CensorInterval(start, end, (detection,)))

    candidates.sort(key=lambda interval: (interval.start, interval.end))
    if not candidates:
        return []

    merge_gap = merge_gap_ms / 1000
    merged: list[CensorInterval] = [candidates[0]]
    for candidate in candidates[1:]:
        current = merged[-1]
        if candidate.start <= current.end + merge_gap:
            merged[-1] = CensorInterval(
                start=current.start,
                end=max(current.end, candidate.end),
                matches=current.matches + candidate.matches,
            )
        else:
            merged.append(candidate)
    return merged


def total_censorship_duration(intervals: Sequence[CensorInterval]) -> float:
    """Return the total duration covered by non-overlapping intervals."""
    return sum(max(0.0, interval.end - interval.start) for interval in intervals)

