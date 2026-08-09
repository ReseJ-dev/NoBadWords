"""Command-line entry point for NoBadWords."""

import argparse
from collections.abc import Sequence

from censor.config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    return argparse.ArgumentParser(
        prog="censor",
        description="Automatically censor profanity in video speech.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line application."""
    configure_logging()
    parser = build_parser()
    parser.parse_args(argv)
    return 0

