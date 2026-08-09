"""Shared domain model foundations.

Processing-specific models will be introduced with the features that use them.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VideoFile:
    """A video selected for future processing."""

    path: Path

