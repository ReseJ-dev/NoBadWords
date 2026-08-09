# NoBadWords

NoBadWords is a desktop application for automatically censoring profanity in
video speech. The current version provides the desktop interface foundation;
transcription and media processing will be added in later commits.

## Requirements

- Python 3.12 or newer

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
python -m app.main
```

The desktop window contains placeholders for video input, scan settings,
detected profanity, and export controls.
