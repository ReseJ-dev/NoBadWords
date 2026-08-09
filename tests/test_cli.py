"""Tests for the initial command-line interface."""

from censor.main import build_parser, main


def test_parser_has_application_description() -> None:
    parser = build_parser()

    assert "profanity" in parser.description.lower()


def test_main_accepts_no_arguments() -> None:
    assert main([]) == 0

