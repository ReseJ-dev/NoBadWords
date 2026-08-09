"""Shared data models for the desktop application."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VideoFile:
    """A video selected in the desktop application."""

    path: Path

